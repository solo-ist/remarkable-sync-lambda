"""Client for interacting with reMarkable Cloud via rmapi binary."""

import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path

import boto3

logger = logging.getLogger(__name__)


class RmapiClient:
    """Wrapper around the rmapi binary for reMarkable Cloud access."""

    def __init__(self):
        self._config_dir = None
        self._rmapi_path = self._find_rmapi_binary()

    def _find_rmapi_binary(self) -> str:
        """Locate the rmapi binary."""
        # In Lambda, binary is in the deployment package
        lambda_path = "/var/task/bin/rmapi"
        if os.path.exists(lambda_path):
            return lambda_path

        # Local development - check PATH
        local_path = "rmapi"
        return local_path

    def _ensure_config(self) -> str:
        """
        Ensure rmapi config is available.

        Downloads from Secrets Manager and writes to temp directory.
        Returns path to config directory.
        """
        if self._config_dir:
            return self._config_dir

        # Create temp directory for rmapi config
        self._config_dir = tempfile.mkdtemp(prefix="rmapi_")
        config_path = Path(self._config_dir) / ".rmapi"

        # Get config from Secrets Manager
        secret_arn = os.environ.get("RMAPI_CONFIG_SECRET_ARN")

        if secret_arn:
            client = boto3.client("secretsmanager")
            response = client.get_secret_value(SecretId=secret_arn)
            config_content = response["SecretString"]
        else:
            # Local development - use local config
            local_config = Path.home() / ".rmapi"
            if local_config.exists():
                config_content = local_config.read_text()
            else:
                raise RuntimeError("No rmapi config found. Run 'rmapi' locally first to authenticate.")

        config_path.write_text(config_content)
        return self._config_dir

    def _run_rmapi(self, *args) -> str:
        """Run rmapi command and return output."""
        config_dir = self._ensure_config()

        env = os.environ.copy()
        env["HOME"] = config_dir  # rmapi looks for .rmapi in HOME

        cmd = [self._rmapi_path] + list(args)

        logger.info(f"Running rmapi: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=60
        )

        if result.returncode != 0:
            logger.error(f"rmapi error: {result.stderr}")
            raise RuntimeError(f"rmapi failed: {result.stderr}")

        return result.stdout

    def list_notebooks(self) -> list[dict]:
        """
        List all notebooks in reMarkable Cloud.

        Returns list of dicts with: id, name, path, modified
        """
        output = self._run_rmapi("ls", "-r")  # recursive listing

        notebooks = []
        for line in output.strip().split("\n"):
            if not line or line.startswith("[d]"):  # skip directories
                continue

            # Parse rmapi ls output: [f] name
            if line.startswith("[f]"):
                name = line[4:].strip()
                notebooks.append({
                    "id": name,  # rmapi uses name as identifier
                    "name": name,
                    "path": "",  # TODO: parse full path from recursive listing
                })

        return notebooks

    def download_notebook(self, notebook_id: str) -> list[bytes]:
        """
        Download notebook and return pages as PNG images.

        Args:
            notebook_id: Notebook identifier

        Returns:
            List of PNG image bytes, one per page
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / notebook_id

            # Download as PDF (rmapi can export to PDF)
            self._run_rmapi("get", notebook_id, "-o", str(output_path))

            # Find downloaded files
            pages = []

            # rmapi exports as .pdf or directory of .png files
            pdf_path = output_path.with_suffix(".pdf")
            if pdf_path.exists():
                # Convert PDF to images
                pages = self._pdf_to_images(pdf_path)
            else:
                # Check for PNG directory
                png_dir = output_path
                if png_dir.is_dir():
                    for png_file in sorted(png_dir.glob("*.png")):
                        pages.append(png_file.read_bytes())

            if not pages:
                logger.warning(f"No pages found for notebook: {notebook_id}")

            return pages

    def _pdf_to_images(self, pdf_path: Path) -> list[bytes]:
        """Convert PDF to list of PNG images."""
        # Use pdf2image if available, otherwise return empty
        # In production, we'd bundle poppler or use a different approach
        try:
            from pdf2image import convert_from_path

            images = convert_from_path(pdf_path)
            result = []

            for img in images:
                import io
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                result.append(buf.getvalue())

            return result

        except ImportError:
            logger.warning("pdf2image not available, skipping PDF conversion")
            return []
