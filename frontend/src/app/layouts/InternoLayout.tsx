import { Outlet } from 'react-router-dom';
import { SidebarInterno } from '@/components/nav/SidebarInterno';
import { TopbarInterno } from '@/components/nav/TopbarInterno';

export default function InternoLayout() {
  return (
    <div className="min-h-screen bg-background flex">
      <SidebarInterno />
      <div className="flex-1 flex flex-col min-w-0">
        <TopbarInterno />
        <main className="flex-1 p-6 overflow-x-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
