document.getElementById("toggle-mode").addEventListener("click", function() {
    document.body.classList.toggle("night-mode");
});

// Fetch stock data based on input
document.getElementById("stock-form").addEventListener("submit", function(e) {
    e.preventDefault();
    const symbol = document.getElementById("stock-symbol").value;
    fetchStockData(symbol);
});

// Fetch stock data from API (replace with actual API)
function fetchStockData(symbol) {
    // Placeholder: This function should fetch real stock data from an API
    // For now, we’ll simulate with static data for demo purposes

    // Simulate a stock chart
    const stockData = {
        labels: ["January", "February", "March", "April", "May"],
        datasets: [{
            label: symbol + " Stock Price",
            data: [120, 130, 125, 140, 135],
            borderColor: "rgba(75, 192, 192, 1)",
            fill: false
        }]
    };

    renderStockChart(stockData);

    // Display some mock results
    const resultHTML = `
        <h2>${symbol} Stock Analysis</h2>
        <p><strong>Current Price:</strong> $130</p>
        <p><strong>Market Trend:</strong> Bullish</p>
        <p><strong>Last Updated:</strong> February 2025</p>
    `;
    document.getElementById("result").innerHTML = resultHTML;
}

function renderStockChart(stockData) {
    const ctx = document.getElementById("stock-chart").getContext("2d");
    new Chart(ctx, {
        type: "line",
        data: stockData,
        options: {
            responsive: true,
            scales: {
                x: { 
                    beginAtZero: true 
                },
                y: { 
                    beginAtZero: true 
                }
            }
        });
}
