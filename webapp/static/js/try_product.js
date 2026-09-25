const OTHER = "Other (type your own)";

let currentForms = [];

async function fetchJSON(url, opts) {
    const resp = await fetch(url, opts);
    if (!resp.ok) throw new Error(`Request failed: ${resp.status}`);
    return resp.json();
}

function fillSelect(select, options) {
    select.innerHTML = "";
    options.forEach(opt => {
        const el = document.createElement("option");
        el.value = opt;
        el.textContent = opt;
        select.appendChild(el);
    });
}

async function loadCategories() {
    const categories = await fetchJSON("/api/categories");
    fillSelect(document.getElementById("category"), categories);
    if (categories.includes("Zinc")) document.getElementById("category").value = "Zinc";
    await onCategoryChange();
}

async function onCategoryChange() {
    const category = document.getElementById("category").value;

    const [forms, dosage, brands] = await Promise.all([
        fetchJSON(`/api/forms/${encodeURIComponent(category)}`),
        fetchJSON(`/api/dosage/${encodeURIComponent(category)}`),
        fetchJSON(`/api/brands/${encodeURIComponent(category)}`),
    ]);

    currentForms = forms;
    const formSelect = document.getElementById("form");
    fillSelect(formSelect, forms.map(f => `${f.form} (${f.tier})`));

    const brandSelect = document.getElementById("brand");
    fillSelect(brandSelect, [...brands, OTHER]);

    populateDoseOptions(dosage);
    onFormChange();
    await onBrandChange();

    document.getElementById("run-btn").disabled = forms.length === 0;
}

function populateDoseOptions(dosage) {
    const doseSelect = document.getElementById("dose");
    const unitSelect = document.getElementById("unit");
    const options = [];
    const map = {};

    if (dosage) {
        unitSelect.value = dosage.unit || "mg";
        const entries = [
            [dosage.min_effective_dose, "minimum effective"],
            [dosage.optimal_low, "optimal low"],
            [dosage.optimal_high, "optimal high"],
            [dosage.upper_limit, "upper safety limit"],
        ];
        const seen = new Set();
        entries.forEach(([value, label]) => {
            if (value !== null && value !== undefined && value !== "" && !seen.has(value)) {
                seen.add(value);
                const text = `${value}${dosage.unit} (${label})`;
                options.push(text);
                map[text] = value;
            }
        });
    }
    options.push(OTHER);
    fillSelect(doseSelect, options);
    doseSelect.dataset.map = JSON.stringify(map);
    toggleDoseOther();
}

function onFormChange() {
    const formSelect = document.getElementById("form");
    const selectedText = formSelect.value;
    const formName = selectedText.split(" (")[0];
    const match = currentForms.find(f => f.form === formName);

    const useCaseSelect = document.getElementById("use-case");
    let useCases = [];
    if (match && match.use_case) {
        useCases = match.use_case.split(";").map(s => s.trim()).filter(s => s && s !== "none");
    }
    if (useCases.length === 0) useCases = ["general"];
    fillSelect(useCaseSelect, useCases);
}

async function onBrandChange() {
    const category = document.getElementById("category").value;
    const brand = document.getElementById("brand").value;
    const productSelect = document.getElementById("product-name");

    toggleBrandOther();

    if (brand === OTHER) {
        fillSelect(productSelect, [OTHER]);
        toggleProductOther();
        return;
    }
    const products = await fetchJSON(`/api/products/${encodeURIComponent(category)}/${encodeURIComponent(brand)}`);
    fillSelect(productSelect, products.length ? [...products, OTHER] : [OTHER]);
    toggleProductOther();
}

function toggleBrandOther() {
    const isOther = document.getElementById("brand").value === OTHER;
    document.getElementById("brand-other").style.display = isOther ? "block" : "none";
}
function toggleProductOther() {
    const productSelect = document.getElementById("product-name");
    const isOther = productSelect.value === OTHER || productSelect.options.length <= 1;
    document.getElementById("product-name-other").style.display = isOther ? "block" : "none";
}
function toggleDoseOther() {
    const isOther = document.getElementById("dose").value === OTHER;
    document.getElementById("dose-other").style.display = isOther ? "block" : "none";
}

function pillClass(result) {
    if (result === "PASS") return "pill-pass";
    if (result === "FAIL") return "pill-fail";
    if (result === "CONDITIONAL") return "pill-conditional";
    return "pill-notfound";
}

async function runPipeline() {
    const category = document.getElementById("category").value;
    const formText = document.getElementById("form").value;
    const formName = formText.split(" (")[0];
    const tier = formText.match(/\(([^)]+)\)/)?.[1] || "";

    const brandVal = document.getElementById("brand").value;
    const brand = brandVal === OTHER ? document.getElementById("brand-other").value : brandVal;

    const productVal = document.getElementById("product-name").value;
    const product_name = (productVal === OTHER || !productVal)
        ? (document.getElementById("product-name-other").value || `${brand} ${category}`)
        : productVal;

    const doseSelect = document.getElementById("dose");
    const doseMap = JSON.parse(doseSelect.dataset.map || "{}");
    const amount = doseSelect.value === OTHER
        ? parseFloat(document.getElementById("dose-other").value)
        : doseMap[doseSelect.value];

    const payload = {
        category, form: formName, brand, product_name, amount,
        unit: document.getElementById("unit").value,
        claimed_use_case: document.getElementById("use-case").value,
        population: document.getElementById("population").value,
        tier,
        advanced: {
            gmp_body: document.getElementById("gmp-body").value,
            has_batch: document.getElementById("has-batch").checked,
            makes_disease_claim: document.getElementById("makes-disease-claim").checked,
            contraindications_disclosed: document.getElementById("contraindications-disclosed").checked,
            lead: parseFloat(document.getElementById("lead").value),
            mercury: parseFloat(document.getElementById("mercury").value),
            cadmium: parseFloat(document.getElementById("cadmium").value),
            arsenic: parseFloat(document.getElementById("arsenic").value),
            tested_amount: amount,
            disclosure_text: document.getElementById("disclosure-text").value || `Full ingredients listed, ${brand} identity disclosed`,
            cited_dose: parseFloat(document.getElementById("cited-dose").value) || 0,
            cited_form: document.getElementById("cited-form").value,
        },
    };

    const runBtn = document.getElementById("run-btn");
    runBtn.disabled = true;
    runBtn.textContent = "Running (Gate 1 and Gate 3 make live API calls)...";

    try {
        const result = await fetchJSON("/api/run-pipeline", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        renderResults(result);
    } catch (err) {
        document.getElementById("results").innerHTML = `<div class="card-box" style="border-color:var(--fail-text);">Error: ${err.message}</div>`;
        document.getElementById("results").style.display = "block";
    } finally {
        runBtn.disabled = false;
        runBtn.textContent = "Run through the pipeline";
    }
}

function renderResults(result) {
    const gates = [
        ["Gate 0 — Formulation", result.gate0],
        ["Gate 1 — Regulatory", result.gate1],
        ["Gate 2 — Quality", result.gate2],
        ["Gate 3 — Brand Integrity", result.gate3],
        ["Gate 4 — Medical", result.gate4],
    ];

    let html = `<div class="divider"></div>`;
    if (result.stopped_at_gate === null || result.stopped_at_gate === undefined) {
        html += `<div class="card-box" style="border-left:4px solid var(--pass-text);"><strong>Cleared all 5 gates</strong> — Final tier: ${result.final_tier}</div>`;
    } else {
        html += `<div class="card-box" style="border-left:4px solid var(--fail-text);"><strong>Stopped at Gate ${result.stopped_at_gate}</strong> — Tier: ${result.final_tier}</div>`;
    }

    gates.forEach(([name, g]) => {
        if (!g) {
            html += `<div class="card-box"><strong>${name}</strong>: not reached</div>`;
            return;
        }
        html += `
        <div class="card-box">
            <strong>${name}</strong> <span class="pill ${pillClass(g.result)}">${g.result}</span>
            <p style="margin-top:0.6rem; margin-bottom:0; font-size:0.92rem;">${g.explanation}</p>
        </div>`;
    });

    const resultsEl = document.getElementById("results");
    resultsEl.innerHTML = html;
    resultsEl.style.display = "block";
}

document.addEventListener("DOMContentLoaded", () => {
    loadCategories();
    document.getElementById("category").addEventListener("change", onCategoryChange);
    document.getElementById("form").addEventListener("change", onFormChange);
    document.getElementById("brand").addEventListener("change", onBrandChange);
    document.getElementById("dose").addEventListener("change", toggleDoseOther);
    document.getElementById("product-name").addEventListener("change", toggleProductOther);
    document.getElementById("run-btn").addEventListener("click", runPipeline);
});
