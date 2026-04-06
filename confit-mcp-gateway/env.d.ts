declare global {
  interface Env {
    MCP_OBJECT: DurableObjectNamespace;
    CONFIT_API_BASE_URL: string;
  }
}

export {};
