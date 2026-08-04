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
      <nav className="navbar">
        <div className="navbar__content">
          <ul className="navbar__links">
            <li>
              <button className="nav-btn" onClick={() => defilerVers(sectionAccueilRef)}>
                Accueil
              </button>
            </li>
            <li>
              <button className="nav-btn" onClick={() => defilerVers(sectionSyntheseRef)}>
                Synthese
              </button>
            </li>
            <li>
              <button className="nav-btn" onClick={() => defilerVers(sectionEcartsRef)}>
                Ecarts
              </button>
            </li>
          </ul>

          <div className="category-select">
            <label htmlFor="category">Categorie</label>
            <div className="category-select__wrapper">
              <select
                id="category"
                value={selectedCategory}
                onChange={(event) => setSelectedCategory(event.target.value)}
                disabled={!availableCategories.length || loading}
              >
                <option value="">Toutes les categories</option>
                {availableCategories.map((category) => (
                  <option key={category} value={category}>
                    {category}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </nav>

      <main className="app">
        <header ref={sectionAccueilRef} className="header">
          <h1>
            Rapprochement <span className="title-accent">SAA</span> / <span className="title-subtle">Systeme Operant</span>
          </h1>
        </header>

        <section className="source-grid">
          <SourceCard
            marker="SAA"
            label="Archive SAA"
            name={sources?.saa.name || "Chargement..."}
            ready={sources?.saa.exists}
            readyText="Fichier trouve"
            missingText="Fichier introuvable"
          />

          <SourceCard
            marker="D"
            label="Systeme Operant"
            name={sources?.d.name || "Chargement..."}
            ready={sources?.d.exists}
            readyText={`${sources?.d.files || 0} fichier(s) trouve(s)`}
            missingText="Dossier introuvable"
          />
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
              "Lancer le rapprochement"
            )}
          </button>

          <button
            className="btn btn--secondary"
            onClick={reloadSources}
            disabled={loading}
          >
            Relire les fichiers
          </button>
        </section>

        {error && <div className="error-banner">{error}</div>}

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
