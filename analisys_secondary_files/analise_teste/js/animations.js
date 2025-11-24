// Dark Mode Toggle with Plotly sync
(function () {
    const KEY = 'jobobs-dark-mode';
    const switchElement = document.getElementById('darkModeSwitch');
    const htmlEl = document.documentElement;

    function applyDark(isDark) {
        htmlEl.classList.toggle('dark', !!isDark);
        if (switchElement) switchElement.checked = !!isDark;
        syncPlotlyTheme(isDark);
    }

    function syncPlotlyTheme(isDark) {
        if (typeof window.jobObsApplyTheme === 'function') {
            window.jobObsApplyTheme(isDark);
            return;
        }

        const chartDivs = document.querySelectorAll('[id^="grafico-"]');
        chartDivs.forEach(div => {
            if (div.data && div.layout && window.Plotly) {
                const bgColor = isDark ? '#071023' : '#ffffff';
                const textColor = isDark ? '#e6eef8' : '#212529';
                const gridColor = isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)';

                window.Plotly.relayout(div, {
                    'paper_bgcolor': bgColor,
                    'plot_bgcolor': bgColor,
                    'font.color': textColor,
                    'xaxis.gridcolor': gridColor,
                    'yaxis.gridcolor': gridColor
                });
            }
        });
    }

    try {
        const saved = localStorage.getItem(KEY);
        if (saved === '1' || saved === '0') {
            applyDark(saved === '1');
        } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            applyDark(true);
        } else {
            applyDark(false);
        }
    } catch (error) {
        console.error('Error loading dark mode preference:', error);
    }

    if (switchElement) {
        switchElement.addEventListener('change', () => {
            const isDark = !!switchElement.checked;
            applyDark(isDark);
            try {
                localStorage.setItem(KEY, isDark ? '1' : '0');
            } catch (error) {
                console.error('Error saving dark mode preference:', error);
            }
        });
    }
})();

document.addEventListener('DOMContentLoaded', () => {
    const navLinks = Array.from(document.querySelectorAll('a[data-scroll]'));
    const sections = document.querySelectorAll('[data-section]');
    const progressBar = document.querySelector('.scroll-progress .progress-bar');
    const backToTop = document.getElementById('backToTop');
    const heroGlow = document.querySelector('.hero-glow');
    const heroSparkles = document.querySelector('.hero-sparkles');

    // Smooth navigation
    navLinks.forEach(link => {
        link.addEventListener('click', event => {
            const targetSelector = link.getAttribute('href');
            if (!targetSelector || !targetSelector.startsWith('#')) return;

            const target = document.querySelector(targetSelector);
            if (!target) return;

            event.preventDefault();
            const yOffset = 80;
            const y = target.getBoundingClientRect().top + window.scrollY - yOffset;
            window.scrollTo({ top: y, behavior: 'smooth' });

            const navbarCollapse = document.getElementById('mainNavbar');
            if (navbarCollapse && navbarCollapse.classList.contains('show') && window.bootstrap) {
                const collapse = window.bootstrap.Collapse.getInstance(navbarCollapse) || new window.bootstrap.Collapse(navbarCollapse);
                collapse.hide();
            }
        });
    });

    // Scroll progress, hero parallax and back-to-top
    const handleScroll = () => {
        const scrollTop = window.scrollY || document.documentElement.scrollTop;
        const docHeight = document.documentElement.scrollHeight - window.innerHeight;
        const progress = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;

        if (progressBar) {
            progressBar.style.width = `${progress}%`;
        }

        if (backToTop) {
            backToTop.classList.toggle('show', scrollTop > 400);
        }

        if (heroGlow) {
            heroGlow.style.transform = `translate3d(0, ${scrollTop * 0.08}px, 0)`;
        }

        if (heroSparkles) {
            heroSparkles.style.transform = `translate3d(${scrollTop * 0.02}px, ${scrollTop * -0.03}px, 0)`;
        }
    };

    handleScroll();
    window.addEventListener('scroll', handleScroll, { passive: true });

    if (backToTop) {
        backToTop.addEventListener('click', () => {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }

    // Section highlight in navigation
    if ('IntersectionObserver' in window) {
        const sectionObserver = new IntersectionObserver(entries => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const id = entry.target.id ? `#${entry.target.id}` : null;
                    if (!id) return;
                    navLinks.forEach(link => {
                        link.classList.toggle('active', link.getAttribute('href') === id);
                    });
                }
            });
        }, {
            threshold: 0.4,
            rootMargin: '-10% 0px -40% 0px'
        });

        sections.forEach(section => sectionObserver.observe(section));
    }

    // Reveal animations
    const revealTargets = document.querySelectorAll('.chart-section, .insight-card, .trend-card, .stat-card');
    if ('IntersectionObserver' in window) {
        const revealObserver = new IntersectionObserver(entries => {
            entries.forEach(entry => {
                if (!entry.isIntersecting) {
                    return;
                }

                entry.target.classList.add('fade-in');

                if (entry.target.matches('.chart-section')) {
                    // Delay chart redraw to ensure container is fully visible
                    setTimeout(() => {
                        if (typeof window.jobObsRedrawCharts === 'function') {
                            window.jobObsRedrawCharts();
                        } else {
                            const charts = entry.target.querySelectorAll('[id^="grafico-"]');
                            charts.forEach(chartEl => {
                                if (window.Plotly && chartEl.data) {
                                    try {
                                        window.Plotly.Plots.resize(chartEl);
                                        window.Plotly.redraw(chartEl);
                                    } catch (error) {
                                        console.warn('Erro ao redesenhar gráfico:', error);
                                    }
                                }
                            });
                        }
                    }, 150);
                }

                revealObserver.unobserve(entry.target);
            });
        }, {
            threshold: 0.1,
            rootMargin: '0px 0px -10% 0px'
        });

        revealTargets.forEach(target => revealObserver.observe(target));
    } else {
        revealTargets.forEach(target => {
            target.classList.add('fade-in');
            if (target.matches('.chart-section')) {
                setTimeout(() => {
                    if (typeof window.jobObsRedrawCharts === 'function') {
                        window.jobObsRedrawCharts();
                    } else {
                        const charts = target.querySelectorAll('[id^="grafico-"]');
                        charts.forEach(chartEl => {
                            if (window.Plotly && chartEl.data) {
                                try {
                                    window.Plotly.Plots.resize(chartEl);
                                    window.Plotly.redraw(chartEl);
                                } catch (error) {
                                    console.warn('Erro ao redesenhar gráfico:', error);
                                }
                            }
                        });
                    }
                }, 150);
            }
        });
    }

    // Floating card parallax interaction
    document.querySelectorAll('.floating-card').forEach(card => {
        card.addEventListener('mousemove', event => {
            const rect = card.getBoundingClientRect();
            const rotateY = ((event.clientX - rect.left) / rect.width - 0.5) * 10;
            const rotateX = ((event.clientY - rect.top) / rect.height - 0.5) * -10;
            card.style.transform = `rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-6px)`;
        });

        card.addEventListener('mouseleave', () => {
            card.style.transform = '';
        });
    });

    const animateCounters = () => {
        const statValues = document.querySelectorAll('.stat-value');
        statValues.forEach((stat, index) => {
            const target = Number(stat.dataset.target);
            if (Number.isNaN(target)) {
                stat.style.opacity = '1';
                return;
            }
            const format = stat.dataset.format || 'decimal';
            setTimeout(() => runCounter(stat, target, format), index * 140);
        });
    };

    window.addEventListener('load', animateCounters, { once: true });
    if (document.readyState === 'complete') {
        animateCounters();
    }

    window.addEventListener('load', () => {
        if (typeof window.jobObsRedrawCharts === 'function') {
            window.setTimeout(() => window.jobObsRedrawCharts(), 300);
            // Additional redraw for safety
            window.setTimeout(() => window.jobObsRedrawCharts(), 1000);
        }
    }, { once: true });

    function runCounter(element, target, format) {
        const duration = 1400;
        const startTimestamp = performance.now();
        const formatValue = createFormatter(format);

        element.style.opacity = '0';
        element.style.transition = 'opacity 0.6s ease';

        const step = (timestamp) => {
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            const currentValue = target * progress;
            element.textContent = formatValue(currentValue, target);
            element.style.opacity = '1';
            if (progress < 1) {
                window.requestAnimationFrame(step);
            }
        };

        window.requestAnimationFrame(step);
    }

    function createFormatter(format) {
        switch (format) {
            case 'currency-short':
                return (value) => {
                    const inThousands = value / 1000;
                    const formatted = inThousands.toFixed(1).replace('.', ',');
                    return `R$ ${formatted}k`;
                };
            case 'percent':
                return (value, target) => {
                    const safeValue = Math.min(value, target);
                    const fractionDigits = target < 10 ? 1 : 0;
                    const formatted = Number(safeValue).toLocaleString('pt-BR', {
                        minimumFractionDigits: 0,
                        maximumFractionDigits: fractionDigits
                    });
                    return `${formatted}%`;
                };
            case 'decimal':
            default:
                return (value) => new Intl.NumberFormat('pt-BR').format(Math.round(value));
        }
    }
});