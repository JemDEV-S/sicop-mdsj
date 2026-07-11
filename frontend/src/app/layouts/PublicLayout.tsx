import { Outlet } from 'react-router-dom';

export default function PublicLayout() {
  return (
    <div className="min-h-screen bg-white">
      {/* TODO T-37: Header público institucional aquí */}
      <main>
        <Outlet />
      </main>
      {/* TODO T-37: Footer público institucional aquí */}
    </div>
  );
}
