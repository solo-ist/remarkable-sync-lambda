/**
 * Client for reMarkable Cloud using rmapi-js.
 */

import { remarkable, type RemarkableApi, type Entry } from "rmapi-js";

export interface Notebook {
  id: string;
  name: string;
  path: string;
  modified: string;
  type: string;
}

export class RemarkableClient {
  private api: RemarkableApi | null = null;
  private token: string;

  constructor(token: string) {
    this.token = token;
  }

  private async getApi(): Promise<RemarkableApi> {
    if (!this.api) {
      this.api = await remarkable(this.token);
    }
    return this.api;
  }

  /**
   * List all notebooks in reMarkable Cloud.
   */
  async listNotebooks(): Promise<Notebook[]> {
    const api = await this.getApi();
    const items = await api.listItems();

    const notebooks: Notebook[] = [];
    const itemMap = new Map<string, Entry>(items.map((i) => [i.id, i]));

    for (const item of items) {
      // Include both documents and collections (folders)
      notebooks.push({
        id: item.id,
        name: item.visibleName,
        path: this.buildPath(itemMap, item.parent),
        modified: item.lastModified,
        type: item.type,
      });
    }

    return notebooks;
  }

  /**
   * Build the full path for an item by traversing parent folders.
   */
  private buildPath(
    itemMap: Map<string, Entry>,
    parentId: string | undefined
  ): string {
    const pathParts: string[] = [];
    let currentId = parentId;

    while (currentId && currentId !== "" && currentId !== "trash") {
      const parent = itemMap.get(currentId);
      if (!parent) break;

      pathParts.unshift(parent.visibleName);
      currentId = parent.parent;
    }

    return pathParts.join("/");
  }
}
