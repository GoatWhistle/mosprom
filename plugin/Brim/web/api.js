const STORAGE_KEY = "brim-token";

function readToken() {
  const match = /(?:^|[?#&])token=([0-9a-f]+)/.exec(location.search + location.hash);
  if (match) {
    try { sessionStorage.setItem(STORAGE_KEY, match[1]); } catch (error) { }
    history.replaceState(null, "", location.pathname);
    return match[1];
  }
  try { return sessionStorage.getItem(STORAGE_KEY) || ""; } catch (error) { return ""; }
}

export const token = readToken();

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

async function request(path, options) {
  const response = await fetch(path, Object.assign({ cache: "no-store" }, options, {
    headers: Object.assign({ "X-Brim-Token": token }, (options || {}).headers),
  }));
  let payload = null;
  try { payload = await response.json(); } catch (error) { }
  if (!response.ok) throw new ApiError(response.status, (payload && payload.error) || response.statusText);
  return payload;
}

export function action(name, ...args) {
  return request("/api/action", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, args }),
  }).then((payload) => payload.result);
}

export function openPath(path) {
  return request("/api/open", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path }),
  });
}

export function upload(file) {
  return request("/api/upload?name=" + encodeURIComponent(file.name), {
    method: "POST",
    headers: { "Content-Type": "application/octet-stream" },
    body: file,
  });
}

export function downloadUrl(path) {
  return "/api/download?token=" + encodeURIComponent(token) + "&path=" + encodeURIComponent(path);
}

export function poll(onView, onState) {
  let version = -1;
  async function step() {
    try {
      const payload = await request("/api/view?since=" + version);
      onState(null);
      if (payload.version !== version) {
        version = payload.version;
        onView(payload.view);
      }
      setTimeout(step, 0);
    } catch (error) {
      onState(error);
      setTimeout(step, error.status === 401 ? 5000 : 1500);
    }
  }
  step();
}
