// Global Chart Instances
let growthChartInstance = null;
let categoryChartInstance = null;

// App State
let currentMonth = new Date().getMonth() + 1; // Default to current month (9)

// Helper to format currency
function formatKRW(val) {
    if (val === undefined || val === null || isNaN(val)) return '0원';
    return Math.round(val).toLocaleString('ko-KR') + '원';
}

// 1. Initialize Month Selector
function initMonthSelector() {
    const container = document.getElementById('monthButtons');
    if (!container) return;
    container.innerHTML = '';
    
    for (let m = 1; m <= 12; m++) {
        const btn = document.createElement('button');
        btn.className = `month-btn ${m === currentMonth ? 'active' : ''}`;
        btn.innerText = `${m}월`;
        btn.addEventListener('click', () => {
            document.querySelectorAll('.month-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentMonth = m;
            loadDashboardData(m);
        });
        container.appendChild(btn);
    }
}

// 2. Render 2026~2033 Asset Growth Projection Chart
function renderGrowthChart() {
    const canvas = document.getElementById('growthChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const years = ['2026년\n(31세)', '2027년\n(32세)', '2028년\n(33세)', '2029년⭐\n(34세)', '2030년🏆\n(35세)', '2031년\n(36세)', '2032년\n(37세)', '2033년🎯\n(38세)'];
    const netWorthData = [4300, 5800, 7400, 8500, 11000, 12500, 14000, 15500]; // in 10,000 KRW (만 원)

    // Gradient Background
    const gradient = ctx.createLinearGradient(0, 0, 0, 260);
    gradient.addColorStop(0, 'rgba(245, 158, 11, 0.35)');
    gradient.addColorStop(0.5, 'rgba(14, 165, 233, 0.15)');
    gradient.addColorStop(1, 'rgba(11, 13, 20, 0)');

    if (growthChartInstance) {
        growthChartInstance.destroy();
        growthChartInstance = null;
    }

    growthChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: years,
            datasets: [{
                label: '확정 순자산 목표 (만 원)',
                data: netWorthData,
                borderColor: '#fbbf24',
                borderWidth: 3,
                pointBackgroundColor: ['#38bdf8', '#38bdf8', '#38bdf8', '#22d3ee', '#fbbf24', '#a78bfa', '#a78bfa', '#ec4899'],
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 5,
                pointHoverRadius: 8,
                fill: true,
                backgroundColor: gradient,
                tension: 0.35
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.95)',
                    titleColor: '#fbbf24',
                    bodyColor: '#f8fafc',
                    borderColor: 'rgba(255, 255, 255, 0.15)',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: false,
                    callbacks: {
                        label: function(context) {
                            const val = context.raw;
                            if (val >= 10000) {
                                const eok = (val / 10000).toFixed(2);
                                return ` 목표 순자산: ${val.toLocaleString()}만 원 (${eok}억 원)`;
                            }
                            return ` 목표 순자산: ${val.toLocaleString()}만 원`;
                        },
                        afterLabel: function(context) {
                            const index = context.dataIndex;
                            const notes = [
                                '📌 청년도약 30회 완료, ISA 모으기 가동',
                                '📌 도약적금 42회 순항, 퇴직연금 1,220만 돌파',
                                '📌 라이나 종신 10년 완납 1년 전 임박',
                                '⭐ 3월 도약적금 5천만 수령 & 6월 라이나 완납(502만)',
                                '🏆 1억 클럽 공식 돌파! 동양 종신 7년 완납',
                                '📌 동양 종신 원금 돌파(102%), 퇴직연금 2,300만',
                                '📌 동양 종신 9년 차(620만), 퇴직연금 2,600만',
                                '🎯 동양 10년 차(130.11%, 767만 원) 도달 ➔ 1.5억 완벽 정복!'
                            ];
                            return '\n' + notes[index];
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.04)' },
                    ticks: {
                        color: '#94a3b8',
                        font: { family: 'Outfit', size: 10, weight: '600' }
                    }
                },
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: {
                        color: '#64748b',
                        font: { family: 'Outfit', size: 10 },
                        callback: function(val) {
                            if (val >= 10000) return (val / 10000) + '억';
                            return val + '만';
                        }
                    },
                    min: 3000,
                    max: 17000
                }
            }
        }
    });
}

// 3. Render Spending Category Doughnut Chart
function renderCategoryChart(categories) {
    const canvas = document.getElementById('categoryChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const labels = [];
    const data = [];
    const colorPalette = [
        '#f43f5e', '#38bdf8', '#fbbf24', '#a855f7', 
        '#10b981', '#ec4899', '#6366f1', '#06b6d4', 
        '#fb923c', '#8b5cf6', '#14b8a6', '#f472b6'
    ];

    if (categories && typeof categories === 'object') {
        Object.entries(categories).forEach(([cat, val]) => {
            const numVal = Number(val) || 0;
            if (numVal > 0 && !cat.includes('저축') && !cat.includes('적금') && !cat.includes('청약')) {
                labels.push(cat);
                data.push(numVal);
            }
        });
    }

    if (categoryChartInstance) {
        categoryChartInstance.destroy();
        categoryChartInstance = null;
    }

    if (data.length === 0) {
        categoryChartInstance = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['지출 없음 / 집계 대기'],
                datasets: [{
                    data: [1],
                    backgroundColor: ['rgba(255, 255, 255, 0.08)'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: '#94a3b8', font: { family: 'Outfit', size: 11 } }
                    }
                },
                cutout: '70%'
            }
        });
        return;
    }

    categoryChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colorPalette.slice(0, data.length),
                borderColor: '#141826',
                borderWidth: 2,
                hoverOffset: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        color: '#94a3b8',
                        font: { family: 'Outfit', size: 11, weight: '500' },
                        boxWidth: 8,
                        padding: 6
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.95)',
                    titleColor: '#fbbf24',
                    bodyColor: '#f8fafc',
                    borderColor: 'rgba(255, 255, 255, 0.15)',
                    borderWidth: 1,
                    padding: 10,
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const pct = total > 0 ? ((context.raw / total) * 100).toFixed(1) : 0;
                            return ` ${context.label}: ${formatKRW(context.raw)} (${pct}%)`;
                        }
                    }
                }
            },
            cutout: '65%'
        }
    });
}

// 4. Render Calendar Grid
function renderCalendar(year, month, noSpendDays = []) {
    const container = document.getElementById('calendarGrid');
    const header = document.getElementById('calMonthHeader');
    if (!container || !header) return;

    container.innerHTML = '';
    header.innerText = `${year}년 ${month}월`;

    const daysInMonth = new Date(year, month, 0).getDate();
    const firstDayIndex = new Date(year, month - 1, 1).getDay(); // 0 is Sun

    // Empty offset cells
    for (let i = 0; i < firstDayIndex; i++) {
        const cell = document.createElement('div');
        cell.className = 'cal-day empty';
        container.appendChild(cell);
    }

    const today = new Date();
    const isCurrentYearMonth = (year === today.getFullYear() && month === (today.getMonth() + 1));
    const currentDayNum = today.getDate();

    // Days cells
    for (let d = 1; d <= daysInMonth; d++) {
        const cell = document.createElement('div');
        cell.className = 'cal-day';
        cell.innerText = d;

        if (isCurrentYearMonth && d === currentDayNum) {
            cell.classList.add('today');
        }

        if (noSpendDays.includes(d)) {
            cell.classList.add('no-spend');
        } else {
            cell.classList.add('spend');
        }

        container.appendChild(cell);
    }
}

// 5. Update Hyundai Card Diet Tracker
function updateCardDietTracker(transactions = [], consumptionTotal = 0) {
    const progressBar = document.getElementById('dietProgressBar');
    const spentText = document.getElementById('dietSpentAmount');
    const remainingText = document.getElementById('dietRemainingAmount');
    const statusText = document.getElementById('dietStatusText');
    if (!progressBar) return;

    const MONTHLY_TARGET = 500000; // 50만 원

    // Filter Hyundai Card transactions or use consumption total
    let cardSpent = 0;
    transactions.forEach(tx => {
        const acc = (tx.account || '').toLowerCase();
        const type = tx.type || '';
        if (type === '지출' || type === '소비' || type === 'consumption') {
            if (acc.includes('현대') || acc.includes('카드') || acc.includes('hyundai')) {
                cardSpent += (Number(tx.amount) || 0);
            }
        }
    });

    // If specific card filter is empty, fallback to consumptionTotal
    if (cardSpent === 0 && consumptionTotal > 0) {
        cardSpent = consumptionTotal;
    }

    const remaining = Math.max(0, MONTHLY_TARGET - cardSpent);
    const pct = Math.min(100, (cardSpent / MONTHLY_TARGET) * 100);

    progressBar.style.width = `${pct}%`;
    spentText.innerText = formatKRW(cardSpent);
    remainingText.innerText = formatKRW(remaining);

    if (cardSpent <= MONTHLY_TARGET) {
        statusText.innerText = `목표 내 순항 중 (${pct.toFixed(0)}% 사용 / 잔여 ${formatKRW(remaining)})`;
        statusText.style.color = '#34d399';
    } else {
        const over = cardSpent - MONTHLY_TARGET;
        statusText.innerText = `⚠️ 예산 초과 (+${formatKRW(over)})`;
        statusText.style.color = '#fb7185';
    }
}

// 6. Load and Render Dashboard Data
async function loadDashboardData(month) {
    try {
        const titleElem = document.getElementById('ledgerMonthTitle');
        if (titleElem) titleElem.innerText = `2026년 ${month}월 가계부 실시간 현황`;

        const response = await fetch(`/api/data?month=${month}`);
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        const data = await response.json();
        console.log("Yerin Dashboard data:", data);

        const yerinData = data.yerin || {
            summary: { income: 0, consumption: 0, savings: 0, balance: 0 },
            categories: {},
            noSpendDays: [],
            transactions: []
        };

        const summary = yerinData.summary || {};
        const income = Number(summary.income) || 0;
        const consumption = Number(summary.consumption) || 0;
        const savings = Number(summary.savings) || 0;
        const balance = summary.balance !== undefined ? Number(summary.balance) : (income - consumption - savings);

        // Bind Live Metrics
        document.getElementById('liveIncome').innerText = formatKRW(income);
        document.getElementById('liveExpense').innerText = formatKRW(consumption);
        document.getElementById('liveSavings').innerText = formatKRW(savings);
        
        const balanceElem = document.getElementById('liveBalance');
        balanceElem.innerText = formatKRW(balance);
        if (balance < 0) {
            balanceElem.className = 'val expense-color';
        } else {
            balanceElem.className = 'val balance-color';
        }

        let savingsRate = 0;
        if (income > 0) {
            savingsRate = ((savings / income) * 100).toFixed(1);
        }
        document.getElementById('liveSavingsRate').innerText = `저축률: ${savingsRate}%`;

        // Update Charts & Visuals
        renderCategoryChart(yerinData.categories);
        renderCalendar(2026, month, yerinData.noSpendDays);
        updateCardDietTracker(yerinData.transactions, consumption);

    } catch (err) {
        console.error("Error loading Yerin dashboard:", err);
    }
}

// App Initialization
window.addEventListener('DOMContentLoaded', () => {
    initMonthSelector();
    renderGrowthChart();
    loadDashboardData(currentMonth);
});
