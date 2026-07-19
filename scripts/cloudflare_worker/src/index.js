export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const primaryTarget = "http://115.247.189.246:30173";
    const backupTarget = "https://presidio-backend.azurewebsites.net";

    const targetUrl = new URL(url.pathname + url.search, primaryTarget);

    const modifiedHeaders = new Headers(request.headers);
    modifiedHeaders.set("Host", "115.247.189.246:30173");
    modifiedHeaders.set("X-Forwarded-Host", url.hostname);
    modifiedHeaders.set("X-Forwarded-Proto", "https");

    try {
      const init = {
        method: request.method,
        headers: modifiedHeaders,
        redirect: "follow",
      };
      if (request.method !== "GET" && request.method !== "HEAD") {
        init.body = request.body;
      }

      const response = await fetch(targetUrl.toString(), init);
      return response;
    } catch (err) {
      console.warn("Primary static target failed, executing failover to Azure Cloud Backup:", err);
      const backupUrl = new URL(url.pathname + url.search, backupTarget);
      const backupInit = {
        method: request.method,
        headers: modifiedHeaders,
        redirect: "follow",
      };
      if (request.method !== "GET" && request.method !== "HEAD") {
        backupInit.body = request.body;
      }
      return fetch(backupUrl.toString(), backupInit);
    }
  },
};
