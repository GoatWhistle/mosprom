function hasFiles(event) {
  return Array.from(event.dataTransfer ? event.dataTransfer.types : []).includes("Files");
}

export function bindDrop(overlay, blocked, onFiles) {
  let depth = 0;
  window.addEventListener("dragenter", (event) => {
    if (!hasFiles(event)) return;
    event.preventDefault();
    depth++;
    overlay.hidden = blocked();
  });
  window.addEventListener("dragover", (event) => { if (hasFiles(event)) event.preventDefault(); });
  window.addEventListener("dragleave", () => {
    depth = Math.max(0, depth - 1);
    if (!depth) overlay.hidden = true;
  });
  window.addEventListener("drop", (event) => {
    if (!hasFiles(event)) return;
    event.preventDefault();
    depth = 0;
    overlay.hidden = true;
    if (!blocked()) onFiles(event.dataTransfer.files);
  });
}
