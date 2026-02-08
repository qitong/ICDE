import React from 'react';
import { TabBar } from '../workspace/TabBar';
import { Canvas } from '../workspace/Canvas';
import { ExportBar } from '../workspace/ExportBar';

export function MainWorkspace() {
  return (
    <main className="flex-1 h-full flex flex-col bg-background">
      <TabBar />
      <Canvas />
      <ExportBar />
    </main>
  );
}
