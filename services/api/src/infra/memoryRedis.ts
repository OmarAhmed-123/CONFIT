type Entry = { value: string; expiresAt?: number };

export class MemoryRedis {
  private store = new Map<string, Entry>();
  private lists = new Map<string, string[]>();
  private sets = new Map<string, Set<string>>();

  duplicate() {
    return this;
  }

  private isExpired(e: Entry) {
    return typeof e.expiresAt === "number" && Date.now() >= e.expiresAt;
  }

  async get(key: string): Promise<string | null> {
    const e = this.store.get(key);
    if (!e) return null;
    if (this.isExpired(e)) {
      this.store.delete(key);
      return null;
    }
    return e.value;
  }

  async set(key: string, value: string, mode?: "EX", ttlSeconds?: number): Promise<"OK"> {
    const expiresAt = mode === "EX" && ttlSeconds ? Date.now() + ttlSeconds * 1000 : undefined;
    this.store.set(key, { value, expiresAt });
    return "OK";
  }

  async expire(key: string, ttlSeconds: number): Promise<number> {
    const e = this.store.get(key);
    if (!e) return 0;
    e.expiresAt = Date.now() + ttlSeconds * 1000;
    this.store.set(key, e);
    return 1;
  }

  async del(key: string): Promise<number> {
    const a = this.store.delete(key) ? 1 : 0;
    this.lists.delete(key);
    this.sets.delete(key);
    return a;
  }

  async lpush(key: string, value: string): Promise<number> {
    const list = this.lists.get(key) ?? [];
    list.unshift(value);
    this.lists.set(key, list);
    return list.length;
  }

  async ltrim(key: string, start: number, stop: number): Promise<"OK"> {
    const list = this.lists.get(key) ?? [];
    const end = stop + 1;
    this.lists.set(key, list.slice(start, end));
    return "OK";
  }

  async lrange(key: string, start: number, stop: number): Promise<string[]> {
    const list = this.lists.get(key) ?? [];
    const end = stop + 1;
    return list.slice(start, end);
  }

  async sadd(key: string, ...members: string[]): Promise<number> {
    const current = this.sets.get(key) ?? new Set<string>();
    let added = 0;
    for (const member of members) {
      if (!current.has(member)) {
        current.add(member);
        added += 1;
      }
    }
    this.sets.set(key, current);
    return added;
  }

  async smembers(key: string): Promise<string[]> {
    return Array.from(this.sets.get(key) ?? []);
  }

  async srem(key: string, ...members: string[]): Promise<number> {
    const current = this.sets.get(key);
    if (!current) return 0;
    let removed = 0;
    for (const member of members) {
      if (current.delete(member)) {
        removed += 1;
      }
    }
    this.sets.set(key, current);
    return removed;
  }
}

