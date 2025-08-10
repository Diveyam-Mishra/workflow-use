import React from "react";
import { useWorkflow } from "../context/workflow-provider";
import { Button } from "@/components/ui/button";
import { EventViewer } from "./event-viewer";

export const RecordingView: React.FC = () => {
  const { stopRecording, workflow } = useWorkflow();
  const stepCount = workflow?.steps?.length || 0;

  const openOptions = () => chrome.runtime.openOptionsPage();
  const [enableIframes, setEnableIframes] = React.useState(true);
  React.useEffect(() => {
    chrome.storage.sync.get({ enableIframes: true }, (s) =>
      setEnableIframes(!!s.enableIframes)
    );
  }, []);
  const toggleIframes = async () => {
    const next = !enableIframes;
    setEnableIframes(next);
    await chrome.storage.sync.set({ enableIframes: next });
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between p-4 border-b border-border">
        <div className="flex items-center space-x-2">
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
          </span>
          <span className="text-sm font-medium">
            Recording ({stepCount} steps)
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={toggleIframes}
            title="Toggle iframe recording"
          >
            {enableIframes ? "Iframes: On" : "Iframes: Off"}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={openOptions}
            title="Open Options"
          >
            Options
          </Button>
          <Button variant="destructive" size="sm" onClick={stopRecording}>
            Stop Recording
          </Button>
        </div>
      </div>
      <div className="flex-grow overflow-hidden p-4">
        <EventViewer />
      </div>
    </div>
  );
};
