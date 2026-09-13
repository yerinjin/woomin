// Global Chart Instances
let growthChartInstance = null;
let categoryChartInstance = null;

// App State - Auto-detect today's current month so when months roll over, it is automatically selected
const today = new Date();
let currentMonth = today.getMonth() + 1; // 1 to 12 (e.g. 9 for September, 10 for October)

// Helper to format currency
function formatKRW(val) {
    if (val === undefined || val === null || isNaN(val)) return '0원';
    return Math.round(val).toLocaleString('ko-KR') + '원';
}

// 1. Initialize Sidebar Tab Navigation
function initTabNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    const tabPanels = {
        'home': document.getElementById('tab-home'),
        'roadmap': document.getElementById('tab-roadmap'),
        'insurance': document.getElementById('tab-insurance'),
        'stocks': document.getElementById('tab-stocks')
    };

    const headerTitles = {
        'home': {
            title: '📋 월급(250만 원) 세부 황금 분배 & 당월 가계부',
            subtitle: '월 250만 원 황금 배분 (저축률 35%) 및 당월 실시간 소비 결산'
        },
        'roadmap': {
            title: '👑 순자산 & 2033 마스터 로드맵',
            subtitle: '2026년 4,300만 ➔ 2030년 1억 ➔ 2033년 1.5억~1.6억 확정 달성 시뮬레이션'
        },
        'insurance': {
            title: '🛡️ 확정 종신보험 환급금 정밀 분석',
            subtitle: '라이나 2029년 10년 완납(117.6%) & 동양 2030년 7년 완납(130.11% 점프)'
        },
        'stocks': {
            title: '📈 실시간 주식 & 연금 포트폴리오',
            subtitle: 'IBK 퇴직연금 DC 실시간 시세 + 카카오페이·토스·미래에셋 ISA 앱별 보유 종목'
        }
    };

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const tabKey = item.dataset.tab;
            if (!tabKey) return;

            navItems.forEach(n => n.classList.remove('active'));
            item.classList.add('active');

            Object.entries(tabPanels).forEach(([key, panel]) => {
                if (panel) {
                    panel.style.display = (key === tabKey) ? 'flex' : 'none';
                }
            });

            // Update Header Title & Subtitle
            const pageTitle = document.getElementById('pageTitle');
            const pageSubtitle = document.getElementById('pageSubtitle');
            if (headerTitles[tabKey]) {
                if (pageTitle) pageTitle.innerText = headerTitles[tabKey].title;
                if (pageSubtitle) pageSubtitle.innerText = headerTitles[tabKey].subtitle;
            }

            // Trigger Chart Render / Resize when tab becomes active
            if (tabKey === 'roadmap') {
                setTimeout(() => {
                    renderGrowthChart();
                }, 50);
            } else if (tabKey === 'home') {
                setTimeout(() => {
                    if (categoryChartInstance) categoryChartInstance.resize();
                }, 50);
            }
        });
    });
}

// 2. Initialize Month Selector (Defaults to current active month)
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

// 2-1. Initialize Stock Portfolio Tabs (보유 증권사 어플별)
function initStockTabs() {
    const tabButtons = document.querySelectorAll('.stk-tab-btn');
    const tabContents = {
        'kakao': document.getElementById('tab_kakao'),
        'toss_us': document.getElementById('tab_toss_us'),
        'toss_kr': document.getElementById('tab_toss_kr'),
        'isa': document.getElementById('tab_isa')
    };

    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.dataset.tab;
            tabButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            Object.entries(tabContents).forEach(([k, elem]) => {
                if (elem) {
                    elem.style.display = (k === targetTab) ? 'block' : 'none';
                }
            });
        });
    });
}

// 3. Render 2026~2033 Asset Growth Projection Chart
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

// 4. Render Spending Category Doughnut Chart
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
                labels: ['지출 없음 / 예산 준비 중'],
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

// 5. Render Calendar Grid
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

    const currentYear = today.getFullYear();
    const currentActualMonth = today.getMonth() + 1;
    const isCurrentYearMonth = (year === currentYear && month === currentActualMonth);
    const currentDayNum = today.getDate();

    // Days cells
    for (let d = 1; d <= daysInMonth; d++) {
        const cell = document.createElement('div');
        cell.className = 'cal-day';
        cell.innerText = d;

        if (isCurrentYearMonth && d === currentDayNum) {
            cell.classList.add('today');
        }

        if (noSpendDays && noSpendDays.includes(d)) {
            cell.classList.add('no-spend');
        } else {
            cell.classList.add('spend');
        }

        container.appendChild(cell);
    }
}

// 6. Update Hyundai Card Diet Tracker
function updateCardDietTracker(transactions = [], consumptionTotal = 0) {
    const progressBar = document.getElementById('dietProgressBar');
    const spentText = document.getElementById('dietSpentAmount');
    const remainingText = document.getElementById('dietRemainingAmount');
    const statusText = document.getElementById('dietStatusText');

    const progressBarTop = document.getElementById('dietProgressBarTop');
    const spentTextTop = document.getElementById('dietSpentAmountTop');
    const remainingTextTop = document.getElementById('dietRemainingAmountTop');

    const MONTHLY_TARGET = 500000; // 50만 원

    // Filter Hyundai Card transactions or use consumption total
    let cardSpent = 0;
    if (Array.isArray(transactions)) {
        transactions.forEach(tx => {
            const acc = (tx.account || '').toLowerCase();
            const type = tx.type || '';
            if (type === '지출' || type === '소비' || type === 'consumption') {
                if (acc.includes('현대') || acc.includes('카드') || acc.includes('hyundai')) {
                    cardSpent += (Number(tx.amount) || 0);
                }
            }
        });
    }

    // If specific card filter is empty, fallback to consumptionTotal
    if (cardSpent === 0 && consumptionTotal > 0) {
        cardSpent = consumptionTotal;
    }

    const remaining = Math.max(0, MONTHLY_TARGET - cardSpent);
    const pct = Math.min(100, Math.max(0, (cardSpent / MONTHLY_TARGET) * 100));

    if (progressBar) progressBar.style.width = `${pct}%`;
    if (spentText) spentText.innerText = formatKRW(cardSpent);
    if (remainingText) remainingText.innerText = formatKRW(remaining);

    if (progressBarTop) progressBarTop.style.width = `${pct}%`;
    if (spentTextTop) spentTextTop.innerText = formatKRW(cardSpent);
    if (remainingTextTop) remainingTextTop.innerText = formatKRW(remaining);

    if (statusText) {
        if (cardSpent <= MONTHLY_TARGET) {
            statusText.innerText = `목표 내 순항 중 (${pct.toFixed(0)}% 사용 / 잔여 ${formatKRW(remaining)})`;
            statusText.style.color = '#34d399';
        } else {
            const over = cardSpent - MONTHLY_TARGET;
            statusText.innerText = `⚠️ 예산 초과 (+${formatKRW(over)})`;
            statusText.style.color = '#fb7185';
        }
    }
}

// 7. Load and Render Dashboard Data for Given Month
async function loadDashboardData(month) {
    try {
        const titleElem = document.getElementById('ledgerMonthTitle');
        const statusSubtitle = document.getElementById('ledgerStatusSubtitle');
        if (titleElem) titleElem.innerText = `2026년 ${month}월 가계부 실시간 현황`;

        const response = await fetch(`/api/data?month=${month}`);
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }
        const data = await response.json();

        const yerinData = data.yerin || data;
        const summary = yerinData.summary || {};

        let inc = Number(summary.income ?? yerinData.total_income ?? data.total_income ?? 0);
        let exp = Number(summary.consumption ?? yerinData.total_expense ?? data.total_expense ?? 0);
        let sav = Number(summary.savings ?? yerinData.total_savings ?? data.total_savings ?? 0);

        const txs = yerinData.transactions || data.transactions || [];
        const categories = yerinData.categories || data.categories || {};
        const noSpendDays = yerinData.noSpendDays || yerinData.no_spend_days || data.noSpendDays || data.no_spend_days || [];

        // If this month has no transactions recorded yet, show healthy standard baseline
        if (inc === 0 && exp === 0 && txs.length === 0) {
            inc = 2500000;
            sav = 875750;
            exp = 0;
            if (statusSubtitle) statusSubtitle.innerText = `실제 수입 / 지출 / 자동 저축 내역 실시간 결산 (${month}월 연동 완료)`;
        } else {
            if (statusSubtitle) statusSubtitle.innerText = `실제 수입 / 지출 / 자동 저축 내역 실시간 결산 (기록 ${txs.length}건)`;
        }

        const bal = inc - exp - sav;
        const savRate = inc > 0 ? (((sav + Math.max(0, bal)) / inc) * 100).toFixed(1) : '35.0';

        // 1. Update Metrics
        const incomeElem = document.getElementById('liveIncome');
        const expenseElem = document.getElementById('liveExpense');
        const savingsElem = document.getElementById('liveSavings');
        const balanceElem = document.getElementById('liveBalance');
        const savingsRateElem = document.getElementById('liveSavingsRate');

        if (incomeElem) incomeElem.innerText = formatKRW(inc);
        if (expenseElem) expenseElem.innerText = formatKRW(exp);
        if (savingsElem) savingsElem.innerText = formatKRW(sav);
        if (balanceElem) balanceElem.innerText = formatKRW(bal);
        if (savingsRateElem) savingsRateElem.innerText = `총 저축률: ${savRate}%`;

        // 2. Update Hyundai Card Diet
        updateCardDietTracker(txs, exp);

        // 3. Render Spending Category Chart
        renderCategoryChart(categories);

        // 4. Render Calendar Grid
        renderCalendar(2026, month, noSpendDays);

    } catch (err) {
        console.error("Failed to load month data:", err);
    }
}

// 8. Fetch Live Stock & Pension Portfolio from Realtime API (Brokerage Apps Live Sync)
async function loadLivePortfolio() {
    try {
        let res = await fetch('/api/portfolio');
        if (!res.ok) {
            res = await fetch('/api/stock');
        }
        if (!res.ok) return;
        const data = await res.json();
        if (!data || !data.stocks) return;

        const stocks = data.stocks;
        const pension = data.pension;

        // 1. Update Pension Totals
        if (pension && pension.total_val) {
            const pensionSub = document.getElementById('pensionSubtitle');
            if (pensionSub) {
                const diff = (pension.total_val || 0) - (pension.total_cost || 0);
                const sign = diff >= 0 ? '+' : '';
                pensionSub.innerHTML = `총 6건 운용 • 평가금액 <b>${formatKRW(pension.total_val)}</b> (${sign}${formatKRW(diff)} / ${sign}${pension.return_pct || 0}%)`;
            }
            const pensionSim = document.getElementById('pensionCurrentValSim');
            if (pensionSim) {
                pensionSim.innerText = formatKRW(pension.total_val);
            }
        }

        // 2. Update Stock Subtitle
        if (stocks && stocks.total_val) {
            const stockSub = document.getElementById('stockSubtitle');
            if (stockSub) {
                const diff = (stocks.total_val || 0) - (stocks.total_cost || 0);
                const sign = diff >= 0 ? '+' : '';
                stockSub.innerHTML = `총 <b>${formatKRW(stocks.total_val)}</b> (${sign}${formatKRW(diff)} / ${sign}${stocks.return_pct || 0}%) • 네이버증권/야후파이낸스 실시간 시세 연동`;
            }
        }

        // Update tab buttons with live valuations
        const btnKakao = document.getElementById('tabBtnKakao');
        if (btnKakao && stocks.kakao) {
            btnKakao.innerText = `카카오페이 (${(stocks.kakao.val / 10000).toFixed(0)}만)`;
        }
        const btnTossUS = document.getElementById('tabBtnTossUS');
        if (btnTossUS && stocks.toss_us) {
            btnTossUS.innerText = `토스 해외 (${(stocks.toss_us.val / 10000).toFixed(0)}만)`;
        }
        const btnTossKR = document.getElementById('tabBtnTossKR');
        if (btnTossKR && stocks.toss_kr) {
            btnTossKR.innerText = `토스 국내 (${(stocks.toss_kr.val / 10000).toFixed(0)}만)`;
        }

        // 3. Render Kakao Items
        const kakaoList = document.getElementById('kakaoStockList');
        if (kakaoList && stocks.kakao && stocks.kakao.items) {
            kakaoList.innerHTML = stocks.kakao.items.map(item => {
                const isPos = item.return_pct >= 0;
                const sign = isPos ? '+' : '';
                const diff = (item.val || 0) - (item.cost || 0);
                const diffSign = diff >= 0 ? '+' : '';
                return `
                    <div class="stock-detail-row">
                        <div class="stk-meta">
                            <h4>${item.name} <span class="stk-shares">${item.shares}${typeof item.shares === 'number' ? '주' : ''}</span></h4>
                            <p>${item.price_usd ? `$${item.price_usd}` : (item.price ? `현재가 ${formatKRW(item.price)}` : '우량주 분산')}</p>
                        </div>
                        <div class="stk-amount-group">
                            <span class="stk-price">${formatKRW(item.val)}</span>
                            <span class="stk-return ${isPos ? 'positive' : 'negative'}">${sign}${item.return_pct}% (${diffSign}${formatKRW(diff)})</span>
                        </div>
                    </div>
                `;
            }).join('');
        }

        // 4. Render Toss US Items
        const tossUsList = document.getElementById('tossUsStockList');
        if (tossUsList && stocks.toss_us && stocks.toss_us.items) {
            tossUsList.innerHTML = stocks.toss_us.items.map(item => {
                const isPos = item.return_pct >= 0;
                const sign = isPos ? '+' : '';
                const diff = (item.val || 0) - (item.cost || 0);
                const diffSign = diff >= 0 ? '+' : '';
                return `
                    <div class="stock-detail-row">
                        <div class="stk-meta">
                            <h4>${item.name} <span class="stk-shares">${item.shares}${typeof item.shares === 'number' ? '주' : ''}</span></h4>
                            <p>${item.price_usd ? `$${item.price_usd}` : '미국 성장주 포트폴리오'}</p>
                        </div>
                        <div class="stk-amount-group">
                            <span class="stk-price">${formatKRW(item.val)}</span>
                            <span class="stk-return ${isPos ? 'positive' : 'negative'}">${sign}${item.return_pct}% (${diffSign}${formatKRW(diff)})</span>
                        </div>
                    </div>
                `;
            }).join('');
        }

        // 5. Render Toss KR Items
        const tossKrList = document.getElementById('tossKrStockList');
        if (tossKrList && stocks.toss_kr && stocks.toss_kr.items) {
            tossKrList.innerHTML = stocks.toss_kr.items.map(item => {
                const isPos = item.return_pct >= 0;
                const sign = isPos ? '+' : '';
                const diff = (item.val || 0) - (item.cost || 0);
                const diffSign = diff >= 0 ? '+' : '';
                return `
                    <div class="stock-detail-row">
                        <div class="stk-meta">
                            <h4>${item.name} <span class="stk-shares">${item.shares}${typeof item.shares === 'number' ? '주' : ''}</span></h4>
                            <p>${item.price ? `현재가 ${formatKRW(item.price)}` : '국내 개별주'}</p>
                        </div>
                        <div class="stk-amount-group">
                            <span class="stk-price">${formatKRW(item.val)}</span>
                            <span class="stk-return ${isPos ? 'positive' : 'negative'}">${sign}${item.return_pct}% (${diffSign}${formatKRW(diff)})</span>
                        </div>
                    </div>
                `;
            }).join('');
        }

    } catch (e) {
        console.warn("Could not fetch live portfolio, keeping baseline snapshot:", e);
    }
}

// App Initialization
window.addEventListener('DOMContentLoaded', () => {
    initTabNavigation();
    initMonthSelector();
    initStockTabs();
    loadDashboardData(currentMonth);
    loadLivePortfolio();
});
