import React, { useEffect, useState } from "react";
import "./App.css";

const API_URL = "http://localhost:8000";

export default function App() {
  const [sources, setSources] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

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
      const response = await fetch(`${API_URL}/api/compare`, {
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

  const sourcesAreReady =
    sources?.saa.exists && sources?.d.exists;

  return (
    <main className="app">
      <header>
        <h1>Rapprochement SAA / Systeme Operant</h1>
      </header>

      <section className="source-grid">
        <article className="source-card">
          <span>Archive SAA</span>
          <strong>{sources?.saa.name || "Chargement..."}</strong>

          <p className={sources?.saa.exists ? "ready" : "missing"}>
            {sources?.saa.exists
              ? "Fichier trouvé"
              : "Fichier introuvable"}
          </p>
        </article>

        <article className="source-card">
          <span>Systeme Operant</span>
          <strong>{sources?.d.name || "Chargement..."}</strong>

          <p className={sources?.d.exists ? "ready" : "missing"}>
            {sources?.d.exists
              ? `${sources.d.files} fichier(s) trouvé(s)`
              : "Dossier introuvable"}
          </p>
        </article>
      </section>

      <section className="actions">
        <button
          onClick={runComparison}
          disabled={!sourcesAreReady || loading}
        >
          {loading
            ? "Rapprochement en cours..."
            : "Lancer le rapprochement"}
        </button>

        <button
          className="secondary"
          onClick={reloadSources}
          disabled={loading}
        >
          Relire les fichiers
        </button>
      </section>

      {error && <p className="error">{error}</p>}

      {result && (
        <>
          <section className="kpi-grid">
            <Kpi
              label="Messages D"
              value={result.summary.totalD}
            />

            <Kpi
              label="Messages SAA"
              value={result.summary.totalMessagesSaa}
            />

            <Kpi
              label="DataBlocks SAA"
              value={result.summary.totalDataBlocksSaa}
            />

            <Kpi
              label="Doublons"
              value={result.summary.duplicates}
              color="orange"
            />
            <Kpi
              label="Blocs SAA ayant trouvé un équivalent dans le système opérant"
              value={result.summary.matched}
              color="green"
            />

            <Kpi
              label="Blocs absents"
              value={result.summary.missing}
              color="red"
            />
          </section>

          <section className="table-container">
            <h2>Résultats par catégorie</h2>

            <table>
              <thead>
                <tr>
                  <th>Catégorie</th>
                  <th>Messages SAA</th>
                  <th>Blocs trouvés</th>
                </tr>
              </thead>

              <tbody>
                {result.categories.map((category) => (
                  <tr key={category.name}>
                    <td>{category.name}</td>
                    <td>{category.messages}</td>
                    <td>{category.matched}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <a
            className="download"
            href={`${API_URL}${result.reportUrl}`}
          >
            Télécharger le rapport TXT
          </a>
        </>
      )}
    </main>
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
