import { useEffect, useMemo, useState } from "react";
import { fetchScriptRun, fetchScripts, startScript } from "./api";
import type { ScriptDefinition, ScriptRun } from "./types";

interface ScriptsViewProps {
  token: string;
}

type ParameterValues = Record<string, string | number | boolean>;

function initialValues(script: ScriptDefinition): ParameterValues {
  return Object.fromEntries(
    script.parameters.map((parameter) => [parameter.name, parameter.default]),
  );
}

function formatRunTime(value: string | null): string {
  if (!value) return "--";
  return new Date(value).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export default function ScriptsView({ token }: ScriptsViewProps) {
  const [scripts, setScripts] = useState<ScriptDefinition[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [values, setValues] = useState<ParameterValues>({});
  const [run, setRun] = useState<ScriptRun | null>(null);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selected = useMemo(
    () => scripts.find((script) => script.id === selectedId) ?? scripts[0] ?? null,
    [scripts, selectedId],
  );
  const runActive = run?.status === "queued" || run?.status === "running";

  useEffect(() => {
    const controller = new AbortController();
    fetchScripts(token, controller.signal)
      .then(({ scripts: catalog }) => {
        setError(null);
        setScripts(catalog);
        if (catalog[0]) {
          setSelectedId(catalog[0].id);
          setValues(initialValues(catalog[0]));
        }
      })
      .catch((requestError: Error) => {
        if (requestError.name !== "AbortError") setError(requestError.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [token]);

  useEffect(() => {
    if (!run || (run.status !== "queued" && run.status !== "running")) {
      return;
    }
    const controller = new AbortController();
    const timer = window.setInterval(() => {
      fetchScriptRun(run.id, token, controller.signal)
        .then(({ run: nextRun }) => {
          setRun(nextRun);
          setError(null);
        })
        .catch((requestError: Error) => {
          if (requestError.name !== "AbortError") setError(requestError.message);
        });
    }, 1_000);
    return () => {
      controller.abort();
      window.clearInterval(timer);
    };
  }, [run, token]);

  const chooseScript = (script: ScriptDefinition) => {
    setSelectedId(script.id);
    setValues(initialValues(script));
    setRun(null);
    setError(null);
  };

  const launch = async () => {
    if (!selected || runActive) return;
    setStarting(true);
    setError(null);
    try {
      const response = await startScript(selected.id, values, token);
      setRun(response.run);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Script could not start.");
    } finally {
      setStarting(false);
    }
  };

  if (loading) {
    return <section className="scripts-workspace panel">Loading script catalog…</section>;
  }

  return (
    <section className="scripts-workspace">
      <div className="scripts-heading">
        <div>
          <span className="eyebrow">OPERATIONS CONSOLE</span>
          <h1>Scripts</h1>
          <p>Run maintained data, ML, and quality jobs without leaving Tickframe.</p>
        </div>
        <span
          className={`quality-badge ${run?.status === "succeeded" ? "good" : run?.status === "failed" || run?.status === "cancelled" ? "warn" : "neutral"}`}
          aria-live="polite"
        >
          {run?.status ?? `${scripts.length} AVAILABLE`}
        </span>
      </div>

      <div className="scripts-layout">
        <aside className="script-catalog panel" aria-label="Available scripts">
          {scripts.map((script) => (
            <button
              className={selected?.id === script.id ? "active" : ""}
              aria-pressed={selected?.id === script.id}
              disabled={runActive}
              key={script.id}
              type="button"
              onClick={() => chooseScript(script)}
            >
              <small>{script.category}</small>
              <strong>{script.name}</strong>
              <span>{script.description}</span>
            </button>
          ))}
        </aside>

        <article className="script-console panel">
          {error && <p className="script-error" role="alert">{error}</p>}
          {selected ? (
            <>
              <div className="panel-head compact">
                <div>
                  <span className="eyebrow">{selected.category}</span>
                  <strong>{selected.name}</strong>
                </div>
              </div>
              <p className="script-description">{selected.description}</p>

              <form
                className="script-parameter-form"
                onSubmit={(event) => {
                  event.preventDefault();
                  void launch();
                }}
              >
                <div className="script-parameters">
                  {selected.parameters.map((parameter) => (
                    <label className={parameter.kind === "boolean" ? "script-toggle" : ""} key={parameter.name}>
                      <span>{parameter.label}</span>
                      {parameter.kind === "select" ? (
                        <select
                          name={parameter.name}
                          value={String(values[parameter.name] ?? parameter.default)}
                          onChange={(event) => setValues((current) => ({ ...current, [parameter.name]: event.target.value }))}
                        >
                          {parameter.options?.map((option) => <option key={option} value={option}>{option}</option>)}
                        </select>
                      ) : parameter.kind === "boolean" ? (
                        <input
                          name={parameter.name}
                          type="checkbox"
                          checked={Boolean(values[parameter.name])}
                          onChange={(event) => setValues((current) => ({ ...current, [parameter.name]: event.target.checked }))}
                        />
                      ) : (
                        <input
                          autoComplete="off"
                          name={parameter.name}
                          type={parameter.kind === "number" ? "number" : "text"}
                          value={String(values[parameter.name] ?? "")}
                          min={parameter.minimum}
                          max={parameter.maximum}
                          required={parameter.kind === "number"}
                          placeholder={parameter.placeholder}
                          onChange={(event) => setValues((current) => ({
                            ...current,
                            [parameter.name]: parameter.kind === "number" && event.target.value !== ""
                              ? event.target.valueAsNumber
                              : event.target.value,
                          }))}
                        />
                      )}
                    </label>
                  ))}
                </div>

                <button
                  className="script-run-button"
                  type="submit"
                  disabled={starting || runActive}
                >
                  {starting ? "Starting…" : run?.status === "queued" ? "Queued…" : run?.status === "running" ? "Running…" : "Run script"}
                </button>
              </form>

              <div className="script-output">
                <header>
                  <span>OUTPUT</span>
                  <span>started {formatRunTime(run?.startedAt ?? null)}</span>
                  {run?.exitCode !== null && run?.exitCode !== undefined && <span>exit {run.exitCode}</span>}
                </header>
                <pre>{run?.output || (run ? `${run.status}…` : "Select parameters and run the script to see output here.")}</pre>
              </div>
            </>
          ) : (
            <p>No scripts are available.</p>
          )}
        </article>
      </div>
    </section>
  );
}
