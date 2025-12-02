"use client";

import { useState, MouseEvent, useEffect } from "react";
import { createPortal } from "react-dom";

export function MethodologyModal() {
  const [isOpen, setIsOpen] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const openModal = (e: MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsOpen(true);
  };

  const closeModal = (e: MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsOpen(false);
  };

  const modalContent = isOpen ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
          onClick={closeModal}
        >
          <div
            className="relative max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-2xl bg-white shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-8 py-5">
              <h2 className="text-2xl font-bold text-gray-900">
                Methodology: Structural-Epistemic Content Matrix
              </h2>
              <button
                onClick={closeModal}
                className="rounded-full p-2 hover:bg-gray-100 transition-colors"
              >
                <svg className="h-6 w-6 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Content */}
            <div className="px-8 py-8 text-left">
              {/* Executive Summary */}
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-6 mb-8">
                <h3 className="text-lg font-bold text-slate-800 mb-4">Abstract</h3>
                <p className="text-slate-700 mb-4 leading-relaxed">
                  This system implements a <strong>decomposed classification pipeline</strong> for media bias detection. Rather than soliciting holistic judgments from a language model—which introduces unquantifiable variance—we reduce the problem to <strong>22 independent binary classification tasks</strong>, each targeting a discrete rhetorical or epistemic feature.
                </p>
                <p className="text-slate-700 mb-4 leading-relaxed">
                  Outputs are aggregated via <strong>Bayesian-smoothed scoring</strong> to produce two orthogonal metrics: an <em>Ideological Score</em> (measuring causal attribution framing) and an <em>Epistemic Score</em> (measuring information quality). The smoothing prior (K=4) ensures that scores reflect <strong>sustained rhetorical patterns</strong> rather than isolated features, reducing sensitivity to short texts and statistical noise.
                </p>
                <div className="bg-white border border-slate-300 rounded-lg p-4 font-mono text-sm text-slate-800">
                  <p className="mb-1"><strong>Score</strong> = (Σ Signal_A − Σ Signal_B) / (Σ Total + K)</p>
                  <p className="text-slate-500 text-xs">where K = 4 (Laplace smoothing constant)</p>
                </div>
              </div>

              <hr className="my-8 border-gray-200" />

              {/* Architecture */}
              <h3 className="text-xl font-bold text-gray-900 mb-6">System Architecture</h3>
              
              <div className="space-y-6 mb-8">
                <div className="bg-gray-50 rounded-lg p-5">
                  <h4 className="font-semibold text-gray-800 mb-2">1. Atomic Decomposition</h4>
                  <p className="text-gray-700 leading-relaxed">
                    Complex bias detection is decomposed into 22 atomic, binary (0/1) classification tasks. Each task targets a single observable linguistic or rhetorical feature with explicit detection criteria. This eliminates the &quot;black box&quot; problem inherent in holistic LLM judgments.
                  </p>
                  <ul className="mt-3 text-sm text-gray-600 space-y-1">
                    <li>• <strong>Ideological Variables (12):</strong> Detect patterns in causal attribution and moral framing</li>
                    <li>• <strong>Epistemic Variables (10):</strong> Audit sourcing quality, documentation, and rhetorical manipulation</li>
                  </ul>
                </div>

                <div className="bg-gray-50 rounded-lg p-5">
                  <h4 className="font-semibold text-gray-800 mb-2">2. Stateless Processing</h4>
                  <p className="text-gray-700 leading-relaxed">
                    Each variable is evaluated as an <strong>independent query</strong> with no shared context between tasks. This eliminates &quot;momentum bias&quot;—where earlier interpretations influence later ones—ensuring each observation is statistically independent.
                  </p>
                </div>

                <div className="bg-gray-50 rounded-lg p-5">
                  <h4 className="font-semibold text-gray-800 mb-2">3. Bayesian Smoothing</h4>
                  <p className="text-gray-700 leading-relaxed">
                    Raw tag counts are converted to scores using Laplace smoothing with K=4. This establishes a <strong>neutral prior</strong>: the system assumes neutrality until sufficient evidence accumulates. A single detected feature in a short article will not produce an extreme score—only sustained, consistent patterns register as significant.
                  </p>
                </div>
              </div>

              <hr className="my-8 border-gray-200" />

              {/* Theoretical Foundations */}
              <h3 className="text-xl font-bold text-gray-900 mb-6">Theoretical Foundations</h3>

              <div className="space-y-6">
                <div>
                  <h4 className="font-semibold text-gray-800 mb-3">Ideological Dimension: Causal Attribution Theory</h4>
                  <p className="text-gray-700 leading-relaxed mb-3">
                    We operationalize ideology not as policy preference but as <strong>cognitive framing of causality</strong>:
                  </p>
                  <ul className="text-gray-700 space-y-2 ml-4">
                    <li>• <strong>Systemic Attribution (Left):</strong> Problems framed as failures of systems—capitalism, structural racism, institutional power. Based on Lakoff&apos;s <em>Moral Politics</em> (2002).</li>
                    <li>• <strong>Agentic Attribution (Right):</strong> Problems framed as failures of individuals—personal responsibility, discipline, law-breaking. Based on Haidt&apos;s <em>The Righteous Mind</em> (2012).</li>
                    <li>• <strong>Moral Foundation Activation:</strong> Detection of Care/Fairness frames (Left) vs. Authority/Sanctity/Order frames (Right).</li>
                  </ul>
                </div>

                <div>
                  <h4 className="font-semibold text-gray-800 mb-3">Epistemic Dimension: Information Quality Audit</h4>
                  <p className="text-gray-700 leading-relaxed mb-3">
                    We measure adherence to journalistic verification standards vs. propagandistic techniques:
                  </p>
                  <ul className="text-gray-700 space-y-2 ml-4">
                    <li>• <strong>High Integrity Markers:</strong> Primary documentation, adversarial sourcing, methodological transparency. Based on Kovach & Rosenstiel&apos;s <em>Elements of Journalism</em> (2001).</li>
                    <li>• <strong>Low Integrity Markers:</strong> Emotive adjectives, reductive labeling, causal certainty on complex issues, imperative address. Based on Benkler et al.&apos;s <em>Network Propaganda</em> (2018).</li>
                  </ul>
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="sticky bottom-0 border-t bg-gray-50 px-8 py-5">
              <button
                onClick={closeModal}
                className="w-full rounded-lg bg-crimson px-4 py-3 text-sm font-semibold text-white hover:bg-crimson/90 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
  ) : null;

  return (
    <>
      <button
        onClick={openModal}
        className="text-[10px] text-gray-500 hover:text-crimson underline underline-offset-2 transition-colors"
      >
        Methodology
      </button>
      {mounted && createPortal(modalContent, document.body)}
    </>
  );
}
