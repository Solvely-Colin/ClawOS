import net from "node:net";

export function surfaceSocketPath(env = process.env) {
  return env.CLAWOS_SURFACE_SOCKET || "/run/clawos-control/surface.sock";
}

export function requestSurface(request, options = {}) {
  const socketPath = options.socketPath || surfaceSocketPath(options.env);
  const timeoutMs = options.timeoutMs || 5000;
  return new Promise((resolve, reject) => {
    const socket = net.createConnection(socketPath);
    let response = "";
    const timeout = setTimeout(() => socket.destroy(new Error("ClawOS surface service timed out.")), timeoutMs);
    socket.setEncoding("utf8");
    socket.on("connect", () => socket.write(`${JSON.stringify(request)}\n`));
    socket.on("data", (chunk) => { response += chunk; });
    socket.on("error", reject);
    socket.on("close", () => {
      clearTimeout(timeout);
      if (!response.trim()) return reject(new Error("ClawOS surface service is unavailable."));
      try {
        const parsed = JSON.parse(response.trim());
        if (!parsed.ok) reject(new Error(parsed.error || "ClawOS surface request failed."));
        else resolve(parsed.result);
      } catch (error) {
        reject(error);
      }
    });
  });
}

export function toolResult(result) {
  return {
    content: [{ type: "text", text: JSON.stringify(result) }],
    details: result,
  };
}
