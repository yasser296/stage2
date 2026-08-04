import React, { useEffect, useRef, useState } from "react";
import "./App.css";

const API_URL = "http://localhost:8000";

export default function App() {
  const [sources, setSources] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("");

  const sectionAccueilRef = useRef(null);
  const sectionSyntheseRef = useRef(null);
  const sectionEcartsRef = useRef(null);

  const defilerVers = (referenceElement) => {
    if (referenceElement.current) {
      referenceElement.current.scrollIntoView({ behavior: "smooth" });
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

      const response = await fetch(compareUrl, {
        method: "POST",
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Le rapprochement a échoué.");
      }

      setResult(data);
    } catch (exception) {
      setError(exception.message);
    } finally {
      setLoading(false);
    }
  }

  async function reloadSources() {
    await fetch(`${API_URL}/api/reload-sources`, {
      method: "POST",
    });

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
            </div>
          </div>
        </div>
      </nav>

      <main className="app">
        <header ref={sectionAccueilRef} className="header">
          <h1 className="header__title">
            Rapprochement
            <span className="header__title-accent"> SAA</span>
            <span className="header__title-separator"> / </span>
            <span className="header__title-subtle">Système Opérant</span>
          </h1>
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
              <span className="source-card__label">Archive SAA : </span>
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
              <span className="source-card__label">Système Opérant : </span>
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
            Relire les fichiers
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
              <SectionHeader title="Synthese des resultats" />

              <div className="kpi-grid">
                <Kpi label="Messages D" value={result.summary.totalD} />
                <Kpi label="Messages SAA" value={result.summary.totalMessagesSaa} />
                <Kpi label="DataBlocks SAA" value={result.summary.totalDataBlocksSaa} />
                <Kpi label="Doublons" value={result.summary.duplicates} color="orange" />
                <Kpi
                  label="Correspondances trouvees"
                  value={result.summary.matched}
                  color="green"
                />
                <Kpi label="Blocs absents" value={result.summary.missing} color="red" />
              </div>
            </section>

            <section ref={sectionEcartsRef} className="table-section">
              <SectionHeader title="Resultats par categorie" />

              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Categorie</th>
                      <th>Messages SAA</th>
                      <th>Blocs trouves</th>
                    </tr>
                  </thead>

                  <tbody>
                    {result.categories.map((category) => (
                      <tr key={category.name}>
                        <td>
                          <span className="category-badge">{category.name}</span>
                        </td>
                        <td>{category.messages}</td>
                        <td className="td-success">{category.matched}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <a className="download-btn" href={`${API_URL}${result.reportUrl}`}>
              Telecharger le rapport TXT
            </a>
          </>
        )}
      </main>
    </div>
  );
}

function SourceCard({ marker, label, name, ready, readyText, missingText }) {
  return (
    <article className="source-card">
      <div className={`source-card__marker source-card__marker--${marker.toLowerCase()}`}>
        {marker}
      </div>
      <div>
        <span className="source-card__label">{label}</span>
        <strong className="source-card__name">{name}</strong>
        <p className={`source-card__status ${ready ? "ready" : "missing"}`}>
          <span className="status-indicator"></span>
          {ready ? readyText : missingText}
        </p>
      </div>
    </article>
  );
}

function SectionHeader({ title }) {
  return (
    <div className="section-header">
      <h2>{title}</h2>
      <div className="section-divider"></div>
    </div>
  );
}

function Kpi({ label, value, color = "blue" }) {
  return (
    <article className={`kpi kpi--${color}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}
