import { useEffect, useRef, useState } from 'react';
import gsap from 'gsap';

interface ObraPhotoItem {
  id: string;
  imagen: string;
  anguloBaraja: number; // Ángulo para que asomen en la baraja inicial
  grupo: 1 | 2 | 3;     // 1: Superior izquierda, 2: Centro (Hero único), 3: Inferior derecha
  isHero?: boolean;     // La única imagen que permanece tras la explosión
}

// Fotografías reales de OBRAS - SIGAT con proporción original 3:2 (2048x1365) sin recortes
const OBRAS_DATA: ObraPhotoItem[] = [
  // Cartas que vuelan hacia la punta superior izquierda y se difuminan
  {
    id: '1',
    imagen: '/obras/486333777_1056925463144744_7235890130926122124_n.jpg',
    anguloBaraja: -16,
    grupo: 1,
  },
  {
    id: '2',
    imagen: '/obras/549285108_1200268395477116_4037664823477546900_n.jpg',
    anguloBaraja: 13,
    grupo: 1,
  },
  {
    id: '3',
    imagen: '/obras/obra-3.jpg',
    anguloBaraja: -9,
    grupo: 1,
  },

  // Cartas que vuelan hacia la punta inferior derecha y se difuminan
  {
    id: '4',
    imagen: '/obras/obra-5.jpg',
    anguloBaraja: 8,
    grupo: 3,
  },
  {
    id: '5',
    imagen: '/obras/obra-7.jpg',
    anguloBaraja: -4,
    grupo: 3,
  },

  // LA ÚNICA IMAGEN QUE PERMANECE TRAS LA EXPLOSIÓN (Dimensiones originales 3:2 sin recorte)
  {
    id: '6',
    imagen: '/obras/799283679_28811691101853258_3705260113283840604_n.jpg',
    anguloBaraja: 0.5,
    grupo: 2,
    isHero: true,
  },
];

function getRandom(min: number, max: number): number {
  return Math.random() * (max - min) + min;
}

export function HeroImageStack() {
  const containerRef = useRef<HTMLDivElement>(null);
  const cardRefs = useRef<(HTMLDivElement | null)[]>([]);
  const [isExploded, setIsExploded] = useState(false);
  const timelineRef = useRef<gsap.core.Timeline | null>(null);

  useEffect(() => {
    const ctx = gsap.context(() => {
      iniciarAnimacion();
    }, containerRef);

    return () => ctx.revert();
  }, []);

  const iniciarAnimacion = () => {
    if (timelineRef.current) {
      timelineRef.current.kill();
    }
    setIsExploded(false);

    const tl = gsap.timeline({
      onComplete: () => setIsExploded(true),
    });
    timelineRef.current = tl;

    // FASE 1: Preparar todas las fotos arriba con opacidad 0
    cardRefs.current.forEach((card, i) => {
      if (!card) return;
      const item = OBRAS_DATA[i];
      if (!item) return;

      gsap.set(card, {
        xPercent: -50,
        yPercent: -50,
        left: '50%',
        top: '50%',
        x: 0,
        y: -100,
        scale: 0.88,
        rotation: item.anguloBaraja * 1.4,
        opacity: 0,
        pointerEvents: 'auto',
        zIndex: i + 1,
        boxShadow: '0 25px 50px -15px rgba(0,0,0,0.32)',
      });
    });

    // FASE 2: Apilar una tras otra en el centro como una baraja de fotos
    // Conservando su formato rectangular original (3:2) con esquinas asomando
    cardRefs.current.forEach((card, i) => {
      if (!card) return;
      const item = OBRAS_DATA[i];
      if (!item) return;

      tl.to(
        card,
        {
          duration: 0.45,
          ease: 'power2.out',
          opacity: 1,
          y: 0,
          scale: 1,
          rotation: item.anguloBaraja,
        },
        0.15 + i * 0.2, // Caída secuencial
      );
    });

    // FASE 3: Pausa para ver la baraja completa armada (0.85s)
    tl.addLabel('barajaArmada', '+=0.85');

    // FASE 4: EXPLOSIÓN
    // Las cartas secundarias se dividen en 2 grupos diagonales y se difuminan hasta desaparecer
    // Solo queda la imagen elegida por el usuario en sus dimensiones originales sin recorte
    cardRefs.current.forEach((card, i) => {
      if (!card) return;
      const item = OBRAS_DATA[i];
      if (!item) return;

      if (item.isHero) {
        // La imagen que permanece sola al centro
        tl.to(
          card,
          {
            duration: 1.2,
            ease: 'expo.out',
            left: '50%',
            top: '50%',
            x: 0,
            y: 0,
            rotation: 0, // Recta y perfectamente encuadrada
            scale: 1.05,
            opacity: 1,
            zIndex: 30,
            boxShadow: '0 30px 60px -15px rgba(0,0,0,0.38)',
          },
          'barajaArmada+=0.1',
        );
      } else {
        // Las demás fotos: vuelan hacia las esquinas opuestas de la diagonal y se difuminan a 0
        let blastX = 0;
        let blastY = 0;
        let blastRot = 0;

        if (item.grupo === 1) {
          // Vuelan hacia la punta superior izquierda
          blastX = getRandom(-340, -200);
          blastY = getRandom(-260, -140);
          blastRot = getRandom(-30, -10);
        } else {
          // Vuelan hacia la punta inferior derecha
          blastX = getRandom(200, 340);
          blastY = getRandom(140, 260);
          blastRot = getRandom(10, 30);
        }

        tl.to(
          card,
          {
            duration: 0.85,
            ease: 'power3.out',
            x: blastX,
            y: blastY,
            rotation: blastRot,
            scale: 0.7,
            opacity: 0, // Se difuminan completamente
            pointerEvents: 'none',
          },
          'barajaArmada',
        );
      }
    });
  };

  const handleHeroHover = () => {
    if (!isExploded) return;
    const heroCard = cardRefs.current[5];
    if (heroCard) {
      gsap.to(heroCard, {
        scale: 1.1,
        duration: 0.35,
        ease: 'power2.out',
        boxShadow: '0 35px 70px -18px rgba(0,0,0,0.45)',
      });
    }
  };

  const handleHeroLeave = () => {
    if (!isExploded) return;
    const heroCard = cardRefs.current[5];
    if (heroCard) {
      gsap.to(heroCard, {
        scale: 1.05,
        duration: 0.45,
        ease: 'power2.out',
        boxShadow: '0 30px 60px -15px rgba(0,0,0,0.38)',
      });
    }
  };

  return (
    <div
      ref={containerRef}
      className="relative w-full h-[380px] sm:h-[450px] md:h-[500px] lg:h-[560px] xl:h-[600px] select-none overflow-hidden sm:overflow-visible flex items-center justify-center"
    >

      {/* Renderizado de las fotos con sus dimensiones originales 3:2 (sin recortes cuadrados) */}
      {OBRAS_DATA.map((obra, index) => (
        <div
          key={obra.id}
          ref={(el) => { cardRefs.current[index] = el; }}
          onMouseEnter={obra.isHero ? handleHeroHover : undefined}
          onMouseLeave={obra.isHero ? handleHeroLeave : undefined}
          className="absolute cursor-default"
        >
          {/* Tarjeta con proporción original 3:2 (2048x1365 original), sin recortes ni distorsión */}
          <div className="relative w-64 sm:w-80 md:w-96 lg:w-[440px] xl:w-[480px] aspect-[3/2] overflow-hidden bg-muted shadow-2xl">
            <img
              src={obra.imagen}
              alt=""
              loading="eager"
              className="w-full h-full object-cover"
            />
          </div>
        </div>
      ))}
    </div>
  );
}

export default HeroImageStack;
