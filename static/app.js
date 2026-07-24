const BENCHMARK_INPUT = "أنا واقف قدام العمارة بتاعة شقة 102 في سموحة وعايز أدخل أشوفها حالاً، ولو غير متاحة أو محتاجة إذن الساكن احجزلي شقة 105 في جليم الساعة 8 المغرب النهاردة، أو قولّي أقرب ميعاد لشقة 102 عشان مسافر القاهرة!";

document.addEventListener('DOMContentLoaded', () => {
    const inputArea = document.getElementById('user-input');
    const runAllBtn = document.getElementById('run-all-btn');
    const resetDbBtn = document.getElementById('reset-db-btn');
    const fillBenchmarkBtn = document.getElementById('fill-benchmark-btn');

    fillBenchmarkBtn.addEventListener('click', () => {
        inputArea.value = BENCHMARK_INPUT;
    });

    resetDbBtn.addEventListener('click', async () => {
        try {
            resetDbBtn.disabled = true;
            resetDbBtn.innerHTML = '<span class="spinner"></span> Resetting...';
            const res = await fetch('/api/reset-db', { method: 'POST' });
            const data = await res.json();
            alert(data.message || 'Database reset successfully!');
        } catch (err) {
            alert('Failed to reset DB: ' + err.message);
        } finally {
            resetDbBtn.disabled = false;
            resetDbBtn.innerHTML = '🔄 Reset Database';
        }
    });

    runAllBtn.addEventListener('click', async () => {
        const query = inputArea.value.trim() || BENCHMARK_INPUT;
        runAllBtn.disabled = true;
        runAllBtn.innerHTML = '<span class="spinner"></span> Running 4 Agents...';

        try {
            // Ordered logically: Non-ReAct pair first, then ReAct pair side-by-side
            const agentTypes = ['reactive', 'routing', 'unconstrained_react', 'constrained_react'];
            const promises = agentTypes.map(type => 
                fetch(`/api/run/${type}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_input: query })
                }).then(r => r.json())
            );

            const results = await Promise.all(promises);
            
            results.forEach((res, index) => {
                const type = agentTypes[index];
                renderAgentResults(type, res);
            });
        } catch (err) {
            console.error('Error running benchmark agents:', err);
            alert('Error running benchmark agents: ' + err.message);
        } finally {
            runAllBtn.disabled = false;
            runAllBtn.innerHTML = '🚀 Run Benchmark (All 4 Agents)';
        }
    });
});

function renderAgentResults(agentType, data) {
    const container = document.getElementById(`agent-col-${agentType}`);
    if (!container) return;

    // Metrics
    container.querySelector('.val-calls').innerText = data.llm_calls ?? 0;
    container.querySelector('.val-tokens').innerText = (data.total_tokens ?? 0).toLocaleString();
    container.querySelector('.val-latency').innerText = `${data.latency_seconds ?? 0}s`;

    // Final Output Box
    const answerBox = container.querySelector('.final-answer-box');
    answerBox.innerText = data.final_answer || 'No output produced.';

    // Trajectory Steps Container
    const trajectoryDiv = container.querySelector('.trajectory-container');
    trajectoryDiv.innerHTML = '';

    if (!data.trajectory || data.trajectory.length === 0) {
        trajectoryDiv.innerHTML = '<p style="color: var(--text-muted); font-size: 0.85rem;">No step trajectory logged.</p>';
        return;
    }

    data.trajectory.forEach((step, idx) => {
        const stepCard = document.createElement('div');
        stepCard.className = `step-card ${step.is_hallucinated ? 'is-hallucination' : ''}`;

        // Header: Step Number & Action Badge
        const stepHeader = document.createElement('div');
        stepHeader.className = 'step-card-header';
        stepHeader.innerHTML = `
            <span class="step-num-badge">${step.is_hallucinated ? '⚠️ Step ' : 'Step '}${step.step || (idx + 1)}</span>
            <span class="step-action-badge">🛠️ ${escapeHtml(step.action || 'action')}</span>
        `;
        stepCard.appendChild(stepHeader);

        // Thought Block
        if (step.thought) {
            const thoughtDiv = document.createElement('div');
            thoughtDiv.className = 'thought-block';
            thoughtDiv.innerHTML = `🧠 <strong>Reasoning:</strong> ${escapeHtml(step.thought)}`;
            stepCard.appendChild(thoughtDiv);
        }

        // Action Input Chips
        if (step.action_input && Object.keys(step.action_input).length > 0) {
            const chipsDiv = document.createElement('div');
            chipsDiv.className = 'input-chips';
            
            for (const [key, value] of Object.entries(step.action_input)) {
                const valStr = typeof value === 'object' ? JSON.stringify(value) : String(value);
                const chip = document.createElement('span');
                chip.className = 'chip';
                chip.innerHTML = `<span class="chip-key">${escapeHtml(key)}:</span> ${escapeHtml(valStr)}`;
                chipsDiv.appendChild(chip);
            }
            stepCard.appendChild(chipsDiv);
        }

        // Rich Visual Observation Card
        if (step.observation) {
            const obsCard = document.createElement('div');
            const isError = step.is_hallucinated || step.observation.includes('ERROR');
            obsCard.className = `obs-card ${isError ? 'obs-error' : ''}`;
            
            let formattedObs = step.observation;
            try {
                const parsedObs = JSON.parse(step.observation);
                if (typeof parsedObs === 'object' && parsedObs !== null) {
                    formattedObs = renderVisualObservation(parsedObs);
                }
            } catch (e) {
                formattedObs = escapeHtml(step.observation);
            }

            obsCard.innerHTML = `
                <div class="obs-title">${isError ? '⚠️ System Alert' : '👁️ DB Observation'}</div>
                <div>${formattedObs}</div>
            `;
            stepCard.appendChild(obsCard);
        }

        trajectoryDiv.appendChild(stepCard);
    });
}

function renderVisualObservation(obs) {
    let html = '<div style="display: flex; flex-direction: column; gap: 0.3rem;">';
    
    if (obs.message) {
        html += `<div style="font-weight: 600; color: #f8fafc;">${escapeHtml(obs.message)}</div>`;
    }
    
    html += '<div style="display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.2rem;">';
    
    for (const [key, val] of Object.entries(obs)) {
        if (key === 'message') continue;
        let badgeColor = 'rgba(255, 255, 255, 0.1)';
        let textColor = '#e2e8f0';

        if (key === 'is_available' || key === 'status') {
            if (val === true || val === 'confirmed' || val === 'success') {
                badgeColor = 'rgba(16, 185, 129, 0.25)';
                textColor = '#6ee7b7';
            } else if (val === false || val === 'OCCUPIED' || val === 'error') {
                badgeColor = 'rgba(248, 113, 113, 0.25)';
                textColor = '#fca5a5';
            }
        }

        const strVal = typeof val === 'object' ? JSON.stringify(val) : String(val);
        html += `<span style="background: ${badgeColor}; color: ${textColor}; padding: 0.15rem 0.45rem; border-radius: 4px; font-size: 0.75rem; font-family: monospace;">
            <strong>${escapeHtml(key)}:</strong> ${escapeHtml(strVal)}
        </span>`;
    }
    
    html += '</div></div>';
    return html;
}

function escapeHtml(str) {
    if (typeof str !== 'string') return str;
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
