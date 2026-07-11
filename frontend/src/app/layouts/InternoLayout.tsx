import { Outlet } from 'react-router-dom';

export default function InternoLayout() {
  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* TODO: Sidebar institucional aquí */}
      <div className="flex-1 flex flex-col">
        {/* TODO: Topbar institucional aquí */}
        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
