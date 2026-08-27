// Global Chart and State Instances
let parentsChart = null;
let trendChartInstance = null;
let currentMonth = 8; // Default to August

// DOM Elements
const monthPillsContainer = document.getElementById('monthPills');
const incomeTableBody = document.getElementById('incomeTableBody');
const expenseTableBody = document.getElementById('expenseTableBody');
const parentsCalendar = document.getElementById('parentsCalendar');

// Helper to format currency
function formatKRW(val) {
    return Math.round(val).toLocaleString('ko-KR') + '원';
}

// Sidebar Tab Switching
function initTabNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    const panels = document.querySelectorAll('.tab-panel');
    const activeTabTitle = document.getElementById('activeTabTitle');

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const selectedTab = item.getAttribute('data-tab');
            
            navItems.forEach(nav => nav.classList.remove('active'));
            item.classList.add('active');

            const iconSpan = item.querySelector('.nav-icon');
            let titleText = item.innerText;
            if (iconSpan) {
                titleText = titleText.replace(iconSpan.innerText, '').trim();
            }
            activeTabTitle.innerText = titleText;

            panels.forEach(panel => {
                panel.classList.remove('active');
                if (panel.id === `panel-${selectedTab}`) {
                    panel.classList.add('active');
                }
            });
        });
    });
}

// Generate Month Pills Selector
function initMonthPills() {
    monthPillsContainer.innerHTML = '';
    for (let m = 1; m <= 12; m++) {
        const btn = document.createElement('button');
        btn.className = `month-pill ${m === currentMonth ? 'active' : ''}`;
        btn.innerText = `${m}월`;
        btn.addEventListener('click', () => {
            document.querySelectorAll('.month-pill').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentMonth = m;
            loadParentsData(m);
        });
        monthPillsContainer.appendChild(btn);
    }
}

// Render Calendar Grid
function renderParentsCalendar(year, month, noSpendDays) {
    parentsCalendar.innerHTML = '';
    document.getElementById('calMonthTitle').innerText = `${year}년 ${month}월`;
    
    const daysInMonth = new Date(year, month, 0).getDate();
    const firstDayIndex = new Date(year, month - 1, 1).getDay(); // 0 is Sun, 6 is Sat
    
    // Empty offsets
    for (let i = 0; i < firstDayIndex; i++) {
        const cell = document.createElement('div');
        cell.className = 'parents-cal-day empty';
        parentsCalendar.appendChild(cell);
    }
    
    // Calendar numbers
    for (let d = 1; d <= daysInMonth; d++) {
        const cell = document.createElement('div');
        cell.className = 'parents-cal-day';
        cell.innerText = d;
        
        if (year === 2026 && month === 8 && d === 26) {
            cell.classList.add('today');
        }
        
        if (noSpendDays.includes(d)) {
            cell.classList.add('no-spend');
        }
        
        parentsCalendar.appendChild(cell);
    }
}

// Render Doughnut Chart
function renderParentsDoughnut(categories) {
    const ctx = document.getElementById('overviewChart').getContext('2d');
    
    const labels = [];
    const data = [];
    const colors = [
        '#3b82f6', '#ef4444', '#10b981', '#f59e0b', 
        '#8b5cf6', '#ec4899', '#06b6d4', '#14b8a6', 
        '#10b981', '#84cc16', '#eab308', '#6366f1'
    ];
    
    Object.entries(categories).forEach(([cat, val]) => {
        if (val > 0 && cat !== '기타') {
            labels.push(cat);
            data.push(val);
        }
    });
    
    if (categories['기타'] > 0) {
        labels.push('기타');
        data.push(categories['기타']);
    }

    if (parentsChart) {
        parentsChart.destroy();
    }

    if (data.length === 0) {
        parentsChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['지출 없음'],
                datasets: [{
                    data: [1],
                    backgroundColor: ['#f1f5f9'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false } }
            }
        });
        return;
    }

    parentsChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors.slice(0, data.length),
                borderColor: '#ffffff',
                borderWidth: 2,
                hoverOffset: 6
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        color: '#475569',
                        font: {
                            family: 'Outfit',
                            size: 13,
                            weight: '600'
                        },
                        boxWidth: 12,
                        padding: 10
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
            cutout: '60%'
        }
    });
}

// Render Combination Bar + Line Chart (Matching User Mockup)
async function loadYearlyTrendChart() {
    try {
        const response = await fetch('/api/yearly-trend');
        if (!response.ok) {
            throw new Error(`Trend API error: ${response.status}`);
        }
        
        const trendData = await response.json();
        console.log("Yearly trend data received:", trendData);

        const labels = trendData.map(d => `${d.month}월`);
        const incomes = trendData.map(d => d.income);
        const consumptions = trendData.map(d => d.consumption);
        const balances = trendData.map(d => d.balance);

        const ctx = document.getElementById('trendChart').getContext('2d');
        
        if (trendChartInstance) {
            trendChartInstance.destroy();
        }

        trendChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        type: 'line',
                        label: '추정 저축액 (당월 잔액)',
                        data: balances,
                        borderColor: '#10b981',
                        borderWidth: 3,
                        pointBackgroundColor: '#10b981',
                        pointBorderColor: '#ffffff',
                        pointHoverRadius: 6,
                        tension: 0.35,
                        fill: false,
                        yAxisID: 'y'
                    },
                    {
                        type: 'bar',
                        label: '총 수입',
                        data: incomes,
                        backgroundColor: '#3b82f6',
                        borderRadius: 6,
                        barPercentage: 0.6,
                        categoryPercentage: 0.7,
                        yAxisID: 'y'
                    },
                    {
                        type: 'bar',
                        label: '소비 지출',
                        data: consumptions,
                        backgroundColor: '#ef4444',
                        borderRadius: 6,
                        barPercentage: 0.6,
                        categoryPercentage: 0.7,
                        yAxisID: 'y'
                    }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: '#475569',
                            font: {
                                family: 'Outfit',
                                size: 12,
                                weight: '600'
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return ` ${context.dataset.label}: ${formatKRW(context.raw)}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: {
                            color: '#64748b',
                            font: { family: 'Outfit', weight: '600' }
                        }
                    },
                    y: {
                        grid: { color: '#f1f5f9' },
                        ticks: {
                            color: '#64748b',
                            font: { family: 'Outfit' },
                            callback: function(value) {
                                if (value >= 100000000) return (value / 100000000) + '억원';
                                if (value >= 10000) return (value / 10000) + '만원';
                                return value;
                            }
                        }
                    }
                }
            }
        });

    } catch (err) {
        console.error("Error loading yearly trend chart:", err);
    }
}

// Bind SVG Loan Progress Gauge
function bindLoanGauge(loan, month) {
    if (!loan) {
        document.getElementById('loanVal').innerText = '0원';
        return;
    }
    
    document.getElementById('loanVal').innerText = formatKRW(loan.totalPayment);

    const total = loan.totalLoan;
    const balance = loan.balance;
    const repaid = total - balance;
    const pct = repaid / total;
    const pctStr = (pct * 100).toFixed(1) + '%';
    const circumference = 2 * Math.PI * 76;
    const offset = circumference - (pct * circumference);

    // 1. Bind Standalone Tab 4
    document.getElementById('loanMonthLabel').innerText = `2026년 ${month}월`;
    document.getElementById('loanGaugePct').innerText = pctStr;
    document.getElementById('loanRepaidAmt').innerText = formatKRW(repaid);
    document.getElementById('loanStatBalance').innerText = formatKRW(balance);
    document.getElementById('loanStatTotal').innerText = formatKRW(loan.totalPayment);
    document.getElementById('loanStatPrincipal').innerText = formatKRW(loan.principal);
    document.getElementById('loanStatInterest').innerText = formatKRW(loan.interest);
    
    const circle = document.getElementById('loanProgressRing');
    if (circle) {
        circle.style.strokeDasharray = `${circumference} ${circumference}`;
        circle.style.strokeDashoffset = offset;
    }

    // 2. Bind Overview Tab Section
    document.getElementById('loanMonthLabelOverview').innerText = `2026년 ${month}월`;
    document.getElementById('loanGaugePctOverview').innerText = pctStr;
    document.getElementById('loanRepaidAmtOverview').innerText = formatKRW(repaid);
    document.getElementById('loanStatBalanceOverview').innerText = formatKRW(balance);
    document.getElementById('loanStatTotalOverview').innerText = formatKRW(loan.totalPayment);
    document.getElementById('loanStatPrincipalOverview').innerText = formatKRW(loan.principal);
    document.getElementById('loanStatInterestOverview').innerText = formatKRW(loan.interest);

    const circleOverview = document.getElementById('loanProgressRingOverview');
    if (circleOverview) {
        circleOverview.style.strokeDasharray = `${circumference} ${circumference}`;
        circleOverview.style.strokeDashoffset = offset;
    }
}

// Populate Tables
function populateTables(transactions, fixedExpenses) {
    incomeTableBody.innerHTML = '';
    expenseTableBody.innerHTML = '';
    const fixedExpenseTableBody = document.getElementById('fixedExpenseTableBody');
    if (fixedExpenseTableBody) fixedExpenseTableBody.innerHTML = '';

    // Fixed Expenses
    let fixedTotal = 0;
    if (fixedExpenses && fixedExpenses.length > 0 && fixedExpenseTableBody) {
        fixedExpenses.sort((a, b) => new Date(a.date) - new Date(b.date)).forEach(tx => {
            fixedTotal += tx.amount;
            const tr = document.createElement('tr');
            const combinedDesc = [tx.subcategory, tx.desc].filter(Boolean).join(' / ') || '-';
            tr.innerHTML = `
                <td>${tx.date}</td>
                <td><span class="category-badge">${tx.category}</span></td>
                <td>${combinedDesc}</td>
                <td class="text-right expense-text">${formatKRW(tx.amount)}</td>
            `;
            fixedExpenseTableBody.appendChild(tr);
        });
        document.getElementById('fixedExpenseTotal').innerText = formatKRW(fixedTotal);
    } else if (fixedExpenseTableBody) {
        fixedExpenseTableBody.innerHTML = '<tr><td colspan="4" class="empty-state">고정지출 내역이 없습니다.</td></tr>';
        document.getElementById('fixedExpenseTotal').innerText = '0 원';
    }

    const incomes = transactions.filter(t => t.type === '수입');
    const expenses = transactions.filter(t => t.type === '지출');

    // 1. Income
    if (incomes.length === 0) {
        incomeTableBody.innerHTML = '<tr><td colspan="5" class="empty-state">해당 월에 수입 내역이 없습니다.</td></tr>';
    } else {
        incomes.forEach(tx => {
            const tr = document.createElement('tr');
            const combinedDesc = [tx.subcategory, tx.desc].filter(Boolean).join(' / ') || '-';
            tr.innerHTML = `
                <td>${tx.date}</td>
                <td><strong>${tx.category}</strong></td>
                <td>${tx.subcategory || '-'}</td>
                <td>${tx.desc || '-'}</td>
                <td class="text-right savings-text">${formatKRW(tx.amount)}</td>
            `;
            incomeTableBody.appendChild(tr);
        });
    }

    // 2. Expense
    if (expenses.length === 0) {
        expenseTableBody.innerHTML = '<tr><td colspan="6" class="empty-state">해당 월에 지출 내역이 없습니다.</td></tr>';
    } else {
        expenses.forEach(tx => {
            const tr = document.createElement('tr');
            const combinedDesc = [tx.subcategory, tx.desc].filter(Boolean).join(' / ') || '-';
            tr.innerHTML = `
                <td>${tx.date}</td>
                <td>${tx.account}</td>
                <td><span class="category-badge">${tx.category}</span></td>
                <td>${combinedDesc}</td>
                <td>${tx.detail || '-'}</td>
                <td class="text-right expense-text">${formatKRW(tx.amount)}</td>
            `;
            expenseTableBody.appendChild(tr);
        });
    }


}

// Fetch Parents Account Data
async function loadParentsData(month) {
    try {
        const response = await fetch(`/api/data?month=${month}`);
        if (!response.ok) {
            throw new Error(`API load failure: ${response.status}`);
        }
        
        const data = await response.json();
        const pData = data.parents;

        const badge = document.getElementById('parentsSourceBadge');
        if (pData.isFallback) {
            badge.innerText = `${pData.fallbackMonth}월 결산 내역 (가장 최신 데이터)`;
            badge.className = 'subtitle warn-text';
        } else {
            badge.innerText = `실시간 연동 완료 (2026 우민 가계부.xlsx)`;
            badge.className = 'subtitle';
        }

        const summary = pData.summary;
        document.getElementById('incomeVal').innerText = formatKRW(summary.income);
        document.getElementById('expenseVal').innerText = formatKRW(summary.consumption);
        
        const balElem = document.getElementById('balanceVal');
        balElem.innerText = formatKRW(summary.balance);
        if (summary.balance < 0) {
            balElem.className = 'stat-value expense-text';
        } else {
            balElem.className = 'stat-value savings-text';
        }

        bindLoanGauge(pData.loan, pData.isFallback ? pData.fallbackMonth : month);
        renderParentsDoughnut(pData.categories);
        renderParentsCalendar(2026, month, pData.noSpendDays);
        populateTables(pData.transactions, pData.fixedExpenses);

        // Render AI Report
        const aiReportContainer = document.getElementById('ai-report-content');
        if (aiReportContainer) {
            if (data.ai_report) {
                aiReportContainer.innerHTML = marked.parse(data.ai_report);
            } else {
                aiReportContainer.innerHTML = '<p class="empty-state" style="padding: 20px; text-align: center; color: #666;">해당 월의 AI 분석 리포트가 아직 생성되지 않았습니다.</p>';
            }
        }
    } catch (err) {
        console.error("Error fetching parents account book data:", err);
    }
}

// App Entry
window.addEventListener('DOMContentLoaded', () => {
    initTabNavigation();
    initMonthPills();
    loadParentsData(currentMonth);
    loadYearlyTrendChart(); // Load the yearly trend combination chart
});
