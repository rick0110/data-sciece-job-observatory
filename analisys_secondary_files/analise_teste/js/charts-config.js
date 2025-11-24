// Charts configuration and orchestration
document.addEventListener('DOMContentLoaded', () => {
    if (!window.Plotly) {
        console.error('Plotly.js não carregado. Os gráficos não serão renderizados.');
        return;
    }

    const chartRegistry = [];
    const isDarkInitial = document.documentElement.classList.contains('dark');

    const themePalette = {
        light: {
            bg: '#ffffff',
            text: '#212529',
            grid: 'rgba(0,0,0,0.1)'
        },
        dark: {
            bg: '#071023',
            text: '#e6eef8',
            grid: 'rgba(255,255,255,0.1)'
        }
    };

    const baseConfig = {
        responsive: true,
        displayModeBar: false,
        locale: 'pt-BR',
        scrollZoom: false
    };

    const layoutSkeleton = {
        font: {
            family: 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'
        },
        margin: { t: 48, r: 32, b: 64, l: 72 },
        hovermode: 'closest',
        transition: { duration: 300, easing: 'cubic-in-out' },
        xaxis: {
            zeroline: false,
            automargin: true
        },
        yaxis: {
            zeroline: false,
            automargin: true
        }
    };

    const clone = (obj) => (obj === undefined ? obj : JSON.parse(JSON.stringify(obj)));

    const deepMerge = (target, source) => {
        const output = target || {};
        Object.keys(source || {}).forEach(key => {
            const value = source[key];
            if (value && typeof value === 'object' && !Array.isArray(value)) {
                output[key] = deepMerge(output[key] ? clone(output[key]) : {}, value);
            } else {
                output[key] = value;
            }
        });
        return output;
    };

    const buildLayout = (overrides = {}) => deepMerge(clone(layoutSkeleton), overrides);

    const applyTheme = (baseLayout, isDark) => {
        const palette = isDark ? themePalette.dark : themePalette.light;
        const layout = clone(baseLayout) || {};

        layout.paper_bgcolor = palette.bg;
        layout.plot_bgcolor = palette.bg;

        layout.font = layout.font || {};
        layout.font.color = palette.text;

        Object.keys(layout).forEach(key => {
            if (key.startsWith('xaxis') || key.startsWith('yaxis')) {
                layout[key] = layout[key] || {};
                layout[key].gridcolor = palette.grid;
                layout[key].color = palette.text;
                layout[key].tickfont = layout[key].tickfont || {};
                layout[key].tickfont.color = palette.text;
                if (layout[key].title && typeof layout[key].title === 'object') {
                    layout[key].title.font = layout[key].title.font || {};
                    layout[key].title.font.color = palette.text;
                }
            }
        });

        if (layout.legend && typeof layout.legend === 'object') {
            layout.legend.font = layout.legend.font || {};
            layout.legend.font.color = palette.text;
        }

        if (layout.title && typeof layout.title === 'object') {
            layout.title.font = layout.title.font || {};
            layout.title.font.color = palette.text;
        }

        return layout;
    };

    const registerChart = ({ id, data, layout: overrides = {}, config: customConfig = {} }) => {
        const element = document.getElementById(id);
        if (!element) {
            console.warn(`Elemento com id "${id}" não encontrado. Gráfico não renderizado.`);
            return;
        }

        const baseLayout = buildLayout(overrides);
        const themedLayout = applyTheme(baseLayout, isDarkInitial);
        const baseData = clone(data);
        const plotData = clone(data);
        const config = { ...baseConfig, ...customConfig };

        // Ensure container has explicit dimensions
        if (element.offsetHeight === 0) {
            element.style.height = '450px';
        }

        try {
            window.Plotly.newPlot(element, plotData, themedLayout, config);
            
            // Force immediate resize
            setTimeout(() => {
                if (window.Plotly && element.data) {
                    window.Plotly.Plots.resize(element);
                }
            }, 100);
        } catch (error) {
            console.error(`Erro ao criar gráfico ${id}:`, error);
            return;
        }

        chartRegistry.push({
            id,
            element,
            baseData,
            baseLayout,
            config
        });
    };

    // Chart definitions --------------------------------------------------

    registerChart({
        id: 'grafico-salarios-nivel',
        data: [{
            x: ['Júnior', 'Pleno', 'Sênior', 'Especialista'],
            y: [3500, 7000, 12000, 18000],
            type: 'bar',
            marker: {
                color: ['#0d6efd', '#6610f2', '#6f42c1', '#d63384'],
                opacity: 0.9
            },
            text: ['R$ 3.500', 'R$ 7.000', 'R$ 12.000', 'R$ 18.000'],
            textposition: 'outside',
            hovertemplate: '<b>%{x}</b><br>Salário: %{text}<extra></extra>'
        }],
        layout: {
            yaxis: { title: 'Salário médio (R$)' },
            bargap: 0.3,
            margin: { t: 40, b: 80, l: 80, r: 32 }
        }
    });

    registerChart({
        id: 'grafico-modalidades',
        data: [{
            values: [45, 35, 20],
            labels: ['Remoto', 'Híbrido', 'Presencial'],
            type: 'pie',
            hole: 0.45,
            sort: false,
            marker: {
                colors: ['#6f42c1', '#20c997', '#212529'],
                line: { color: '#ffffff', width: 1 }
            },
            hovertemplate: '<b>%{label}</b><br>%{value}% das vagas<extra></extra>'
        }],
        layout: {
            margin: { t: 20, b: 20, l: 20, r: 20 },
            showlegend: true,
            legend: { orientation: 'h', y: -0.2 }
        }
    });

    const anosExperiencia = [0, 2, 4, 6, 8, 10];
    registerChart({
        id: 'grafico-evolucao',
        data: [
            {
                x: anosExperiencia,
                y: [3000, 5500, 8000, 11000, 14000, 16000],
                type: 'scatter',
                mode: 'lines+markers',
                name: 'Desenvolvedor',
                line: { color: '#0d6efd', width: 3, shape: 'spline' },
                marker: { size: 8 },
                hovertemplate: '<b>Desenvolvedor</b><br>Anos: %{x}<br>Salário: R$ %{y:,.0f}<extra></extra>'
            },
            {
                x: anosExperiencia,
                y: [4000, 7000, 10000, 14000, 18000, 22000],
                type: 'scatter',
                mode: 'lines+markers',
                name: 'Cientista de Dados',
                line: { color: '#6610f2', width: 3, shape: 'spline' },
                marker: { size: 8 },
                hovertemplate: '<b>Cientista de Dados</b><br>Anos: %{x}<br>Salário: R$ %{y:,.0f}<extra></extra>'
            }
        ],
        layout: {
            xaxis: { title: 'Anos de experiência' },
            yaxis: { title: 'Salário (R$)' },
            legend: { orientation: 'h', y: -0.2 },
            margin: { t: 40, b: 80, l: 80, r: 32 }
        }
    });

    registerChart({
        id: 'grafico-cargos',
        data: [{
            x: [150, 120, 110, 95, 85, 75, 70, 60, 55, 50],
            y: [
                'Full Stack Developer',
                'Data Scientist',
                'Backend Developer',
                'Frontend Developer',
                'DevOps Engineer',
                'Mobile Developer',
                'Data Engineer',
                'QA Engineer',
                'UX/UI Designer',
                'Product Manager'
            ],
            type: 'bar',
            orientation: 'h',
            marker: {
                color: ['#d63384', '#dc3545', '#fd7e14', '#ffc107', '#20c997', '#0dcaf0', '#0d6efd', '#6610f2', '#6f42c1', '#adb5bd']
            },
            text: ['150 vagas', '120 vagas', '110 vagas', '95 vagas', '85 vagas', '75 vagas', '70 vagas', '60 vagas', '55 vagas', '50 vagas'],
            textposition: 'outside',
            hovertemplate: '<b>%{y}</b><br>%{x} vagas abertas<extra></extra>'
        }],
        layout: {
            xaxis: { title: 'Número de vagas' },
            margin: { t: 40, b: 40, l: 220, r: 40 },
            height: 480
        }
    });

    const setores = ['Serviços Financeiros', 'Tecnologia Corporativa', 'Varejo Digital', 'Consultorias', 'Saúde Tech'];
    registerChart({
        id: 'grafico-setores',
        data: [
            {
                name: 'Júnior',
                x: setores,
                y: [4200, 4500, 3800, 3600, 4000],
                type: 'bar',
                marker: { color: '#0d6efd' }
            },
            {
                name: 'Pleno',
                x: setores,
                y: [7800, 8200, 7200, 6800, 7400],
                type: 'bar',
                marker: { color: '#20c997' }
            },
            {
                name: 'Sênior',
                x: setores,
                y: [15200, 18800, 16200, 15400, 16800],
                type: 'bar',
                marker: { color: '#6610f2' }
            }
        ],
        layout: {
            barmode: 'group',
            bargap: 0.25,
            yaxis: { title: 'Salário médio (R$)' },
            legend: { orientation: 'h', y: -0.25 },
            margin: { t: 40, b: 90, l: 80, r: 40 }
        }
    });

    const trimestres = ['Q1 2025', 'Q2 2025', 'Q3 2025', 'Q4 2025'];
    registerChart({
        id: 'grafico-evolucao-modalidade',
        data: [
            {
                name: 'Remoto',
                x: trimestres,
                y: [118, 142, 168, 184],
                type: 'scatter',
                mode: 'lines+markers',
                line: { color: '#6f42c1', shape: 'spline', width: 3 },
                marker: { size: 8 },
                fill: 'tozeroy',
                fillcolor: 'rgba(111,66,193,0.12)',
                hovertemplate: '<b>Remoto</b><br>%{x}: %{y} vagas<extra></extra>'
            },
            {
                name: 'Híbrido',
                x: trimestres,
                y: [96, 110, 128, 140],
                type: 'scatter',
                mode: 'lines+markers',
                line: { color: '#20c997', shape: 'spline', width: 3 },
                marker: { size: 8 },
                hovertemplate: '<b>Híbrido</b><br>%{x}: %{y} vagas<extra></extra>'
            },
            {
                name: 'Presencial',
                x: trimestres,
                y: [72, 78, 84, 92],
                type: 'scatter',
                mode: 'lines+markers',
                line: { color: '#fd7e14', shape: 'spline', width: 3 },
                marker: { size: 8 },
                hovertemplate: '<b>Presencial</b><br>%{x}: %{y} vagas<extra></extra>'
            }
        ],
        layout: {
            xaxis: { title: 'Trimestres de 2025' },
            yaxis: { title: 'Vagas publicadas' },
            legend: { orientation: 'h', y: -0.25 },
            margin: { t: 40, b: 90, l: 80, r: 32 }
        }
    });

    const beneficiosRotulo = [
        'Plano de saúde premium',
        'Bônus anual de performance',
        'Home office flexível',
        'Ajuda de custo para setup',
        'Programas de educação contínua',
        'Stock options'
    ];
    const beneficiosValores = [82, 74, 68, 63, 59, 35];
    registerChart({
        id: 'grafico-beneficios',
        data: [{
            x: beneficiosValores.slice().reverse(),
            y: beneficiosRotulo.slice().reverse(),
            type: 'bar',
            orientation: 'h',
            marker: {
                color: ['#0d6efd', '#6610f2', '#20c997', '#0dcaf0', '#ffc107', '#fd7e14'].reverse(),
                opacity: 0.85
            },
            text: beneficiosValores.slice().reverse().map(v => `${v}%`),
            textposition: 'outside',
            hovertemplate: '<b>%{y}</b><br>Presente em %{x}% das vagas<extra></extra>'
        }],
        layout: {
            xaxis: { title: 'Presença nas vagas analisadas (%)', range: [0, 100] },
            margin: { t: 30, b: 40, l: 260, r: 40 }
        }
    });

    const distribuicaoSalarios = {
        'Desenvolvimento': [3500, 4200, 5200, 6500, 8400, 9600, 11700, 13500, 15200],
        'Dados': [4200, 5600, 7800, 9800, 12500, 15200, 18800, 21000, 24000],
        'Produto': [3600, 4900, 6100, 7800, 9500, 12000, 14500, 16800],
        'Infraestrutura': [3800, 4800, 6200, 7800, 9800, 12500, 14200, 15800]
    };
    const boxColors = ['#0d6efd', '#6f42c1', '#fd7e14', '#20c997'];
    const boxData = Object.keys(distribuicaoSalarios).map((area, index) => ({
        y: distribuicaoSalarios[area],
        name: area,
        type: 'box',
        marker: { color: boxColors[index % boxColors.length] },
        boxmean: true,
        jitter: 0.35,
        pointpos: 0,
        boxpoints: 'suspectedoutliers',
        hovertemplate: `<b>${area}</b><br>R$ %{y:,.0f}<extra></extra>`
    }));

    registerChart({
        id: 'grafico-box-salarios',
        data: boxData,
        layout: {
            boxmode: 'group',
            yaxis: { title: 'Faixa salarial (R$)' },
            margin: { t: 40, b: 60, l: 90, r: 40 }
        }
    });

    // Theme bridge for dark-mode toggle
    const cloneData = (data) => clone(data);

    window.jobObsCharts = chartRegistry;
    window.jobObsApplyTheme = (isDark) => {
        chartRegistry.forEach(chart => {
            const themedLayout = applyTheme(chart.baseLayout, isDark);
            const data = cloneData(chart.baseData);
            window.Plotly.react(chart.element, data, themedLayout, chart.config);
        });
    };

    window.jobObsRedrawCharts = () => {
        chartRegistry.forEach(chart => {
            if (chart.element && chart.element.data) {
                try {
                    window.Plotly.Plots.resize(chart.element);
                    window.Plotly.redraw(chart.element);
                } catch (error) {
                    console.warn(`Erro ao redesenhar gráfico ${chart.id}:`, error);
                }
            }
        });
    };

    window.addEventListener('resize', () => {
        chartRegistry.forEach(chart => {
            if (chart.element && chart.element.data) {
                try {
                    window.Plotly.Plots.resize(chart.element);
                } catch (error) {
                    console.warn(`Erro ao redimensionar gráfico ${chart.id}:`, error);
                }
            }
        });
    });

    // Force initial redraw after all charts are loaded
    setTimeout(() => {
        if (typeof window.jobObsRedrawCharts === 'function') {
            window.jobObsRedrawCharts();
        }
    }, 500);
});