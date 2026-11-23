import { ShieldAlert } from "lucide-react";
import useLiveFeed from "../hooks/useLiveFeed";
import { ConnectionBadge } from "../components/Badges";
import { STATE_COLOR, STATE_LABEL } from "../lib/fall";

// One camera: the live picture with person boxes coloured by fall state, the
// camera's name and connection, and its detection status. A confirmed fall puts a
// pulsing red frame around the whole tile so it stands out in a grid of cameras.
export default function CameraTile({ camera, width = 640, skeleton, onOpen }) {
  const { canvasRef, status, live, info } = useLiveFeed(camera, { width, skeleton });
  const worst = info.worst;
  const alarm = worst === "CONFIRMED";
  const possible = worst === "POSSIBLE";

  let detection;
  if (!camera.fall_detection_enabled) detection = ["badge-neutral", "Fall detection off"];
  else if (!live) detection = ["badge-neutral", "Waiting for video"];
  else if (!info.detecting) detection = ["badge-warning", "Starting detection…"];
  else if (alarm) detection = ["badge-danger", "FALL CONFIRMED"];
  else if (possible) detection = ["badge-warning", "Possible fall"];
  else detection = ["badge-success", `Monitoring · ${info.people} ${info.people === 1 ? "person" : "people"}`];

  return (
    <button type="button" onClick={onOpen}
      className={`card overflow-hidden text-left w-full hover:shadow-md transition-shadow ${alarm ? "alert-pulse !border-danger-500 border-2" : possible ? "!border-warning-500 border-2" : ""}`}>
      <div className="aspect-video bg-ink-900 relative flex items-center justify-center">
        <canvas ref={canvasRef} className="w-full h-full object-contain" />
        {!live && (
          <div className="absolute inset-0 flex items-center justify-center text-center text-white/50 text-xs px-4">
            <div>
              <ShieldAlert size={24} className="mx-auto mb-1" />
              {status === "live" ? "Connected — waiting for video" : status === "disabled" ? "Feed switched off" : status === "connecting" ? "Connecting…" : "Offline"}
            </div>
          </div>
        )}
        <span className={`absolute top-2 right-2 badge ${detection[0]}`}>{detection[1]}</span>
        {live && info.detecting && !alarm && !possible && info.worst !== "NORMAL" && (
          <span className="absolute top-2 left-2 badge" style={{ background: STATE_COLOR[info.worst], color: "#fff" }}>{STATE_LABEL[info.worst]}</span>
        )}
      </div>
      <div className="px-4 py-3 flex items-center justify-between gap-2">
        <div className="min-w-0">
          <p className="text-sm font-medium text-ink-900 truncate">{camera.name}</p>
          <p className="text-xs text-slate-400 truncate">{camera.site || "No site"}{info.inferenceMs ? ` · ${info.inferenceMs} ms/frame` : ""}</p>
        </div>
        <ConnectionBadge value={camera.connection} />
      </div>
    </button>
  );
}
