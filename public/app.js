// Global Chart Instances
let yerinChartInstance = null;
let parentsChartInstance = null;

// App State
let currentMonth = 8; // Default to August
let currentViewMode = 'unified'; // 'unified' or 'parents'

// DOM Elements
const monthButtonsContainer = document.getElementById('monthButtons');
const matchedList = document.getElementById('matchedList');
const unmatchedList = document.getElementById('unmatchedList');
const crossCheckSummary = document.getElementById('crossCheckSummary');
const mainDashboardGrid = document.getElementById('mainDashboardGrid');
const yerinDashboard = document.getElementById('yerinDashboard');
const crossCheckPanel = document.getElementById('crossCheckPanel');
const parentsLoanCard = document.getElementById('parentsLoanCard');

// View Mode Buttons
const btnUnified = document.getElementById('viewModeUnified');
const btnParents = document.getElementById('viewModeParents');

// Helper to format currency
function formatKRW(val) {
    return Math.round(val).toLocaleString('ko-KR') + '원';
}

// Generate Month Buttons
function initMonthSelector() {
    monthButtonsContainer.innerHTML = '';
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
        monthButtonsContainer.appendChild(btn);
    }
}

// Initialize View Mode Toggles
function initViewModeSelector() {
    btnUnified.addEventListener('click', () => {
        btnUnified.classList.add('active');
        btnParents.classList.remove('active');
        currentViewMode = 'unified';
        
        // Show Yerin & Cross checks
        yerinDashboard.style.display = '';
        crossCheckPanel.style.display = '';
        mainDashboardGrid.classList.remove('parents-only-view');
    });
    
    btnParents.addEventListener('click', () => {
        btnParents.classList.add('active');
        btnUnified.classList.remove('active');
        currentViewMode = 'parents';
        
        // Hide Yerin & Cross checks
        yerinDashboard.style.display = 'none';
        crossCheckPanel.style.display = 'none';
        mainDashboardGrid.classList.add('parents-only-view');
    });
}

// Render Calendar Grid
function renderCalendar(containerId, headerId, year, month, noSpendDays) {
    const container = document.getElementById(containerId);
    const header = document.getElementById(headerId);
    
    container.innerHTML = '';
    header.innerText = `${year}년 ${month}월`;
    
    const daysInMonth = new Date(year, month, 0).getDate();
    const firstDayIndex = new Date(year, month - 1, 1).getDay(); // 0 is Sun, 6 is Sat
    
    // Render Empty Cells for Offset
    for (let i = 0; i < firstDayIndex; i++) {
        const cell = document.createElement('div');
        cell.className = 'cal-day empty';
        container.appendChild(cell);
    }
    
    // Render Month Days
    for (let d = 1; d <= daysInMonth; d++) {
        const cell = document.createElement('div');
        cell.className = 'cal-day';
        cell.innerText = d;
        
        if (year === 2026 && month === 8 && d === 26) {
            cell.classList.add('today');
        }
        
        // Check if No-Spend Day
        if (noSpendDays.includes(d)) {
            cell.classList.add('no-spend');
        } else {
            cell.classList.add('spend');
        }
        
        container.appendChild(cell);
    }
}

// Create/Update Doughnut Chart
function renderDoughnutChart(canvasId, chartInstanceRef, categories) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    const labels = [];
    const data = [];
    const colors = [
        '#ff5252', '#ff4081', '#e040fb', '#7c4dff', 
        '#536dfe', '#448aff', '#40c4ff', '#18ffff', 
        '#64ffda', '#69f0ae', '#b2ff59', '#eeff41', '#ffd740'
    ];
    
    Object.entries(categories).forEach(([cat, val]) => {
        if (val > 0) {
            labels.push(cat);
            data.push(val);
        }
    });

    if (canvasId === 'yerinChart' && yerinChartInstance) {
        yerinChartInstance.destroy();
    } else if (canvasId === 'parentsChart' && parentsChartInstance) {
        parentsChartInstance.destroy();
    }

    if (data.length === 0) {
        const newInstance = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['지출 없음'],
                datasets: [{
                    data: [1],
                    backgroundColor: ['rgba(255, 255, 255, 0.05)'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false }
                }
            }
        });
        if (canvasId === 'yerinChart') yerinChartInstance = newInstance;
        else parentsChartInstance = newInstance;
        return;
    }

    const newInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors.slice(0, data.length),
                borderColor: '#161a26',
                borderWidth: 2,
                hoverOffset: 6
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        color: '#8e95a7',
                        font: {
                            family: 'Outfit',
                            size: 11
                        },
                        boxWidth: 10,
                        padding: 8
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return ` ${context.label}: ${formatKRW(context.raw)}`;
                        }
                    }
                }
            },
            cutout: '65%'
        }
    });

    if (canvasId === 'yerinChart') yerinChartInstance = newInstance;
    else parentsChartInstance = newInstance;
}

// Bind Metrics
function bindUserMetrics(prefix, stats) {
    const summary = stats.summary;
    document.getElementById(`${prefix}Income`).innerText = formatKRW(summary.income);
    document.getElementById(`${prefix}Consumption`).innerText = formatKRW(summary.consumption);
    document.getElementById(`${prefix}Savings`).innerText = formatKRW(summary.savings);
    
    const balanceElem = document.getElementById(`${prefix}Balance`);
    balanceElem.innerText = formatKRW(summary.balance);
    if (summary.balance < 0) {
        balanceElem.className = 'value expense-color';
    } else {
        balanceElem.className = 'value balance-color';
    }
    
    document.getElementById(`${prefix}SavingsRate`).innerText = `저축률: ${summary.savingsRate}%`;
}

// Bind Mortgage Loan Details
function bindParentsLoan(loan) {
    if (!loan) {
        parentsLoanCard.style.display = 'none';
        return;
    }

    parentsLoanCard.style.display = 'flex';
    
    const total = loan.totalLoan;
    const balance = loan.balance;
    const repaid = total - balance;
    const pct = (repaid / total) * 100;
    
    document.getElementById('loanProgressPct').innerText = `${pct.toFixed(1)}% 상환 완료`;
    document.getElementById('loanProgressBar').style.width = `${pct}%`;
    
    document.getElementById('loanTotal').innerText = formatKRW(total);
    document.getElementById('loanBalance').innerText = formatKRW(balance);
    document.getElementById('loanMonthlyPayment').innerText = formatKRW(loan.totalPayment);
    document.getElementById('loanPrincipal').innerText = formatKRW(loan.principal);
    document.getElementById('loanInterest').innerText = formatKRW(loan.interest);
}

// Load and render data
async function loadDashboardData(month) {
    try {
        const response = await fetch(`/api/data?month=${month}`);
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }
        
        const data = await response.json();
        console.log("Dashboard data received:", data);

        // 1. Bind Yerin Stats
        bindUserMetrics('yerin', data.yerin);
        renderDoughnutChart('yerinChart', yerinChartInstance, data.yerin.categories);
        renderCalendar('yerinCalendar', 'yerinCalMonth', 2026, month, data.yerin.noSpendDays);

        // 2. Bind Parents Stats & Loan
        bindUserMetrics('parents', data.parents);
        bindParentsLoan(data.parents.loan);
        renderDoughnutChart('parentsChart', parentsChartInstance, data.parents.categories);
        renderCalendar('parentsCalendar', 'parentsCalMonth', 2026, month, data.parents.noSpendDays);

        // Update Parents source badge depending on fallback state
        const badge = document.getElementById('parentsSourceBadge');
        if (data.parents.isFallback) {
            badge.innerText = `${data.parents.fallbackMonth}월 결산 내역 (최신)`;
            badge.className = 'data-source-badge warning-badge';
        } else {
            badge.innerText = `${month}월 결산 내역 (Excel)`;
            badge.className = 'data-source-badge';
        }

        // 3. Render Cross-Check list
        matchedList.innerHTML = '';
        unmatchedList.innerHTML = '';

        const cc = data.crossCheck;

        // Render matched items
        if (cc.matched.length === 0) {
            matchedList.innerHTML = '<li class="no-tx-msg">일치하는 거래 내역이 없습니다.</li>';
        } else {
            cc.matched.forEach(item => {
                const li = document.createElement('li');
                li.className = 'match-item';
                li.innerHTML = `
                    <div class="tx-detail">
                        <span class="tx-title">${item.yerin.desc} ↔ ${item.parents.desc}</span>
                        <span class="tx-meta">[${item.date}] 예린(${item.yerin.account}) | 부모님(${item.parents.account})</span>
                    </div>
                    <span class="tx-amount">${formatKRW(item.amount)}</span>
                `;
                matchedList.appendChild(li);
            });
        }

        // Render unmatched items
        const unmatchedCount = cc.unmatched_yerin.length + cc.unmatched_parents.length;
        if (unmatchedCount === 0) {
            unmatchedList.innerHTML = '<li class="no-tx-msg" style="color: var(--accent-income);">양측 가계부에 불일치하는 연관 거래가 없습니다. 완벽합니다!</li>';
        } else {
            cc.unmatched_yerin.forEach(item => {
                const li = document.createElement('li');
                li.innerHTML = `
                    <div class="tx-detail">
                        <span class="tx-title"><span style="color:#a5b4fc">[예린 가계부만 기록]</span> ${item.desc}</span>
                        <span class="tx-meta">[${item.date}] 계정: ${item.category} | 결제: ${item.account}</span>
                    </div>
                    <span class="tx-amount">${formatKRW(item.amount)}</span>
                `;
                unmatchedList.appendChild(li);
            });

            cc.unmatched_parents.forEach(item => {
                const li = document.createElement('li');
                li.innerHTML = `
                    <div class="tx-detail">
                        <span class="tx-title"><span style="color:#fb923c">[부모님 가계부만 기록]</span> ${item.desc}</span>
                        <span class="tx-meta">[${item.date}] 계정: ${item.category} | 결제: ${item.account}</span>
                    </div>
                    <span class="tx-amount">${formatKRW(item.amount)}</span>
                `;
                unmatchedList.appendChild(li);
            });
        }

        // Update Cross Check Badge Status
        crossCheckSummary.innerText = `정산 ${cc.matched.length}건 확인됨 / 미매칭 ${unmatchedCount}건`;
        if (unmatchedCount > 0) {
            crossCheckSummary.style.background = 'rgba(255, 77, 77, 0.15)';
            crossCheckSummary.style.color = '#ff8a80';
            crossCheckSummary.style.border = '1px solid rgba(255, 77, 77, 0.3)';
        } else {
            crossCheckSummary.style.background = 'rgba(0, 230, 118, 0.15)';
            crossCheckSummary.style.color = '#b9f6ca';
            crossCheckSummary.style.border = '1px solid rgba(0, 230, 118, 0.3)';
        }

    } catch (err) {
        console.error("Error loading dashboard metrics:", err);
    }
}

// App Initialization
window.addEventListener('DOMContentLoaded', () => {
    initMonthSelector();
    initViewModeSelector();
    loadDashboardData(currentMonth);
});
