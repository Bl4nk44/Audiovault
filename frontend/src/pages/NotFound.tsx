// import React from 'react'
import { Link } from "react-router-dom";
import { Home, AlertCircle } from "lucide-react";

const NotFound = () => {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-background text-foreground p-4">
      <div className="text-center space-y-6 max-w-md">
        <div className="flex justify-center">
          <AlertCircle className="w-24 h-24 text-primary animate-pulse" />
        </div>

        <h1 className="text-6xl font-bold tracking-tighter">404</h1>
        <h2 className="text-2xl font-semibold text-muted-foreground">
          Strona nie została znaleziona
        </h2>

        <p className="text-muted-foreground">
          Wygląda na to, że zabłądziłeś w muzycznej przestrzeni. Ta ścieżka nie istnieje lub została
          przeniesiona.
        </p>

        <div className="pt-6">
          <Link
            to="/"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-primary text-primary-foreground hover:bg-primary/90 transition-colors font-medium"
          >
            <Home className="w-4 h-4" />
            Wróć do strony głównej
          </Link>
        </div>
      </div>
    </div>
  );
};

export default NotFound;
