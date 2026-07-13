import { Outlet } from 'react-router-dom';
import { HeaderPublico } from '@/components/nav/HeaderPublico';
import { FooterPublico } from '@/components/nav/FooterPublico';

export default function PublicLayout() {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      <HeaderPublico />
      <main className="flex-1">
        <Outlet />
      </main>
      <FooterPublico />
    </div>
  );
}
