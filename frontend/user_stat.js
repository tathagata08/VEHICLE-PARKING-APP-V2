async function renderUserStats(reservations) {
    if (!reservations || reservations.length === 0) return;
    const urlParams = new URLSearchParams(window.location.search);
    const uid = urlParams.get("uid");

    const userToken = localStorage.getItem("token");
    const adminToken = localStorage.getItem("admin_token");

    let url, token;
    if (uid && adminToken) {
        url = `http://127.0.0.1:5000/admin/user/${uid}/history`;
        token = adminToken;
    } else if (!uid && userToken) {
        url = "http://127.0.0.1:5000/user/history";
        token = userToken;
    } else {
        console.error("No valid token available.");
        return;
    }

    try {
        const res = await fetch(url, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        if (!res.ok) throw new Error("Failed to fetch history");

        const data = await res.json();
        const reservations = data.history || [];

        // ======= PIE CHART DATA =======
        const activeCount = reservations.filter(r => !r.released_at).length;
        const releasedCount = reservations.filter(r => r.released_at).length;

        const pieCtx = document.getElementById("statusPieChart")?.getContext("2d");
        if (pieCtx) {
            new Chart(pieCtx, {
                type: "pie",
                data: {
                    labels: ["Active", "Released"],
                    datasets: [{
                        data: [activeCount, releasedCount],
                        backgroundColor: ["#dc3545", "#28a745"]
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { position: "bottom" },
                        title: { display: true, text: "Reservation Status" }
                    }
                }
            });
        }

        // ======= LINE CHART DATA =======
        const occupancyMap = {};
        reservations.forEach(r => {
            const start = new Date(r.reserved_at);
            const end = r.released_at ? new Date(r.released_at) : new Date();

            let current = new Date(start);
            while (current <= end) {
                const key = current.toISOString().split("T")[0];
                occupancyMap[key] = (occupancyMap[key] || 0) + 1;
                current.setDate(current.getDate() + 1);
            }
        });

        const labels = Object.keys(occupancyMap).sort();
        const dataPoints = labels.map(d => occupancyMap[d]);

        const lineCtx = document.getElementById("occupancyLineChart")?.getContext("2d");
        if (lineCtx) {
            new Chart(lineCtx, {
                type: "line",
                data: {
                    labels: labels,
                    datasets: [{
                        label: "Active Reservations",
                        data: dataPoints,
                        borderColor: "#007bff",
                        backgroundColor: "rgba(0,123,255,0.2)",
                        fill: true,
                        tension: 0.3
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { display: true },
                        title: { display: true, text: "Daily Occupancy" }
                    },
                    scales: {
                        x: { title: { display: true, text: "Date" } },
                        y: { title: { display: true, text: "Number of Reservations" }, beginAtZero: true }
                    }
                }
            });
        }

        // ======= REVENUE CHART =======
        const revenueMap = {};
        reservations.forEach(r => {
            const dateKey = new Date(r.reserved_at).toISOString().split("T")[0];
            revenueMap[dateKey] = (revenueMap[dateKey] || 0) + (r.total_cost || 0);
        });

        const revenueLabels = Object.keys(revenueMap).sort();
        const revenueData = revenueLabels.map(d => revenueMap[d]);

        const revenueCtx = document.getElementById("revenueChart")?.getContext("2d");
        if (revenueCtx) {
            new Chart(revenueCtx, {
                type: "bar",
                data: {
                    labels: revenueLabels,
                    datasets: [{
                        label: "Revenue (₹)",
                        data: revenueData,
                        backgroundColor: "#ffc107"
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { display: false },
                        title: { display: true, text: "Revenue per Day" }
                    },
                    scales: {
                        x: { title: { display: true, text: "Date" } },
                        y: { title: { display: true, text: "Revenue (₹)" }, beginAtZero: true }
                    }
                }
            });
        }

    } catch (err) {
        console.error(err);
        alert("Failed to load reservation stats.");
    }
}

window.addEventListener("DOMContentLoaded", renderUserStats);
