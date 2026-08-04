import { useEffect, useState, useRef } from "react";
import "./App.css";

const API_URL = "http://localhost:8000";

interface SourceStatus {
  name: string;
  exists: boolean;
  files?: number;
}

interface Sources {
  saa: SourceStatus;
  d: SourceStatus;
  categories: string[];
}

interface Category {
  name: string;
  messages: number;
  matched: number;
}

interface Summary {
  totalD: number;
  totalMessagesSaa: number;
  totalDataBlocksSaa: number;
  duplicates: number;
  matched: number;
  missing: number;
}

interface Result {
  summary: Summary;
  categories: Category[];
  reportUrl: string;
}

export default function App() {
  const [sources, setSources] = useState<Sources | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("");
  const sectionAccueilRef = useRef<HTMLDivElement>(null);
  const sectionSyntheseRef = useRef<HTMLDivElement>(null);
  const sectionEcartsRef = useRef<HTMLDivElement>(null);

  const defilerVers = (referenceElement: React.RefObject<HTMLDivElement | null>) => {
    if (referenceElement.current) {
      referenceElement.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  async function loadStatus() {
    try {
      const response = await fetch(`${API_URL}/api/status`);
      const data = await response.json();
      setSources(data);
    } catch {
      setError("Impossible de contacter le serveur Python.");
    }
  }

  useEffect(() => {
    loadStatus();
  }, []);

  async function runComparison() {
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const compareUrl = selectedCategory
        ? `${API_URL}/api/compare?category=${encodeURIComponent(selectedCategory)}`
        : `${API_URL}/api/compare`;
      const response = await fetch(compareUrl, { method: "POST" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Le rapprochement a échoué.");
      setResult(data);
    } catch (exception: unknown) {
      setError(exception instanceof Error ? exception.message : "Une erreur est survenue");
    } finally {
      setLoading(false);
    }
  }

  async function reloadSources() {
    await fetch(`${API_URL}/api/reload-sources`, { method: "POST" });
    setResult(null);
    await loadStatus();
  }

  const sourcesAreReady = sources?.saa.exists && sources?.d.exists;
  const availableCategories = sources?.categories || [];

  return (
    <div className="app-wrapper">
      {/* Background decoration */}
      <div className="bg-decoration">
        <div className="bg-orb bg-orb--1"></div>
        <div className="bg-orb bg-orb--2"></div>
        <div className="bg-grid"></div>
      </div>

      <nav className="navbar">
        <div className="navbar__content">
          
          <div className="navbar__brand">
            <div className="brand-mark">
              <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
                <rect width="32" height="32" rx="8" fill="url(#brand-gradient)"/>
                <path d="M8 16L14 10L20 16L14 22L8 16Z" fill="white" opacity="0.9"/>
                <path d="M14 16L20 10L26 16L20 22L14 16Z" fill="white" opacity="0.6"/>
                <defs>
                  <linearGradient id="brand-gradient" x1="0" y1="0" x2="32" y2="32">
                    <stop stopColor="#1a1a2e"/>
                    <stop offset="1" stopColor="#16213e"/>
                  </linearGradient>
                </defs>
              </svg>
              <span className="brand-text">SAA<span className="brand-highlight">Recon</span></span>
            </div>
          </div>
          
          <ul className="navbar__links">
            <li>
              <button className="nav-btn" onClick={() => defilerVers(sectionAccueilRef)}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
                  <polyline points="9 22 9 12 15 12 15 22"/>
                </svg>
                Accueil
              </button>
            </li>
            <li>
              <button className="nav-btn" onClick={() => defilerVers(sectionSyntheseRef)}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
                  <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
                  <line x1="12" y1="22.08" x2="12" y2="12"/>
                </svg>
                Synthèse
              </button>
            </li>
            <li>
              <button className="nav-btn" onClick={() => defilerVers(sectionEcartsRef)}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="20" x2="18" y2="10"/>
                  <line x1="12" y1="20" x2="12" y2="4"/>
                  <line x1="6" y1="20" x2="6" y2="14"/>
                </svg>
                Écarts
              </button>
            </li>
          </ul>

          <div className="category-select">
            <label htmlFor="category">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>
              </svg>
              Catégorie
            </label>
            <div className="category-select__wrapper">
              <select
                id="category"
                value={selectedCategory}
                onChange={event => setSelectedCategory(event.target.value)}
                disabled={!availableCategories.length || loading}
              >
                <option value="">Toutes les catégories</option>
                {availableCategories.map(category => (
                  <option key={category} value={category}>{category}</option>
                ))}
              </select>
              <svg className="select-arrow" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <polyline points="6 9 12 15 18 9"/>
              </svg>
            </div>
          </div>
        </div>
      </nav>

      <main className="app">
        <header className="header" ref={sectionAccueilRef}>
          <div className="header__badge">
            <span className="badge-dot"></span>
            Comparaison en temps réel
          </div>
          <h1 className="header__title">
            Rapprochement
            <span className="header__title-accent"> SAA</span>
            <span className="header__title-separator"> / </span>
            <span className="header__title-subtle">Système Opérant</span>
          </h1>
          <p className="header__subtitle">
            Analyse croisée entre l'archive SAA et les données du système opérant
          </p>
        </header>

        <section className="source-grid">
          <article className="source-card">
            <div className="source-card__icon source-card__icon--saa">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/>
                <line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
            </div>
            <div className="source-card__content">
              <span className="source-card__label">Archive SAA</span>
              <strong className="source-card__name">{sources?.saa.name || "Chargement..."}</strong>
              <p className={`source-card__status ${sources?.saa.exists ? "source-card__status--ready" : "source-card__status--missing"}`}>
                <span className="status-indicator"></span>
                {sources?.saa.exists ? "Fichier trouvé" : "Fichier introuvable"}
              </p>
            </div>
          </article>
          <article className="source-card">
            <div className="source-card__icon source-card__icon--system">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
                <line x1="8" y1="21" x2="16" y2="21"/>
                <line x1="12" y1="17" x2="12" y2="21"/>
              </svg>
            </div>
            <div className="source-card__content">
              <span className="source-card__label">Système Opérant</span>
              <strong className="source-card__name">{sources?.d.name || "Chargement..."}</strong>
              <p className={`source-card__status ${sources?.d.exists ? "source-card__status--ready" : "source-card__status--missing"}`}>
                <span className="status-indicator"></span>
                {sources?.d.exists ? `${sources.d.files} fichier(s) trouvé(s)` : "Dossier introuvable"}
              </p>
            </div>
          </article>
        </section>

        <section className="actions">
          <button
            className="btn btn--primary"
            onClick={runComparison}
            disabled={!sourcesAreReady || loading}
          >
            {loading ? (
              <>
                <span className="spinner"></span>
                Analyse en cours...
              </>
            ) : (
              <>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="11" cy="11" r="8"/>
                  <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                </svg>
                Lancer le rapprochement
              </>
            )}
          </button>
          <button
            className="btn btn--secondary"
            onClick={reloadSources}
            disabled={loading}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="23 4 23 10 17 10"/>
              <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
            </svg>
            Recharger
          </button>
        </section>

        {error && (
          <div className="error-banner">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            {error}
          </div>
        )}

        {result && (
          <>
            <section ref={sectionSyntheseRef} className="kpi-section">
              <div className="section-header">
                <h2 className="section-title">Synthèse des résultats</h2>
                <div className="section-divider"></div>
              </div>
              <div className="kpi-grid">
                <Kpi
                  label="Messages Système Opérant"
                  value={result.summary.totalD}
                  icon="database"
                  color="slate"
                />
                <Kpi
                  label="Messages SAA"
                  value={result.summary.totalMessagesSaa}
                  icon="archive"
                  color="indigo"
                />
                <Kpi
                  label="DataBlocks SAA"
                  value={result.summary.totalDataBlocksSaa}
                  icon="layers"
                  color="violet"
                />
                <Kpi
                  label="Doublons"
                  value={result.summary.duplicates}
                  icon="copy"
                  color="amber"
                />
                <Kpi
                  label="Correspondances trouvées"
                  value={result.summary.matched}
                  icon="check-circle"
                  color="emerald"
                  highlight
                />
                <Kpi
                  label="Écarts détectés"
                  value={result.summary.missing}
                  icon="alert-triangle"
                  color="rose"
                />
              </div>
            </section>

            <section ref={sectionEcartsRef} className="table-section">
              <div className="section-header">
                <h2 className="section-title">Résultats par catégorie</h2>
                <div className="section-divider"></div>
              </div>
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>
                        <span className="th-content">
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                          </svg>
                          Catégorie
                        </span>
                      </th>
                      <th>
                        <span className="th-content">
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <rect x="2" y="7" width="20" height="14" rx="2" ry="2"/>
                            <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>
                          </svg>
                          Messages SAA
                        </span>
                      </th>
                      <th>
                        <span className="th-content">
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <polyline points="20 6 9 17 4 12"/>
                          </svg>
                          Correspondances
                        </span>
                      </th>
                      <th>
                        <span className="th-content">
                          Taux de match
                        </span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.categories.map((category: Category) => {
                      const matchRate = category.messages > 0 
                        ? Math.round((category.matched / category.messages) * 100) 
                        : 0;
                      return (
                        <tr key={category.name}>
                          <td>
                            <span className="category-badge">{category.name}</span>
                          </td>
                          <td className="td-number">{category.messages.toLocaleString()}</td>
                          <td className="td-number td-number--success">{category.matched.toLocaleString()}</td>
                          <td>
                            <div className="match-rate">
                              <div className="match-rate__bar">
                                <div 
                                  className="match-rate__fill" 
                                  style={{ width: `${matchRate}%` }}
                                ></div>
                              </div>
                              <span className="match-rate__value">{matchRate}%</span>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>

            <a
              className="download-btn"
              href={`${API_URL}${result.reportUrl}`}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/>
                <line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
              Télécharger le rapport complet
            </a>
          </>
        )}
      </main>
    </div>
  );
}

function Kpi({ label, value, icon, color = "slate", highlight = false }: { label: string; value: number; icon: string; color?: string; highlight?: boolean }) {
  const getIcon = () => {
    switch(icon) {
      case 'database':
        return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>;
      case 'archive':
        return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5"/><line x1="10" y1="12" x2="14" y2="12"/></svg>;
      case 'layers':
        return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>;
      case 'copy':
        return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>;
      case 'check-circle':
        return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>;
      case 'alert-triangle':
        return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>;
      default:
        return null;
    }
  };

  return (
    <article className={`kpi kpi--${color} ${highlight ? 'kpi--highlight' : ''}`}>
      <div className="kpi__header">
        <div className={`kpi__icon kpi__icon--${color}`}>
          {getIcon()}
        </div>
      </div>
      <div className="kpi__body">
        <span className="kpi__label">{label}</span>
        <strong className="kpi__value">{value.toLocaleString()}</strong>
      </div>
    </article>
  );
}
