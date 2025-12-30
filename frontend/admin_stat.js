// Fetch utility
const token = localStorage.getItem("admin_token");
if (!token) window.location.href = "admin_login.html";


async function fetchData(url) {
    const res = await fetch(url, {
        headers: { "Authorization": `Bearer ${token}` }
    });
    if (!res.ok) {
        console.error(`Failed to fetch ${url}`);
        return { labels: [], values: [] };
    }
    return res.json();
}

async function renderCharts() {
    // 1️⃣ Bookings per Lot (Horizontal Bar)
    const bookingsData = await fetchData("http://127.0.0.1:5000/admin/stats/bookings_per_lot");
    const ctxBookings = document.getElementById("chartBookings").getContext("2d");
    new Chart(ctxBookings, {
        type: "bar",
        data: {
            labels: bookingsData.lots,      // <-- use 'lots'
            datasets: [{ 
                label: "Number of Bookings",
                data: bookingsData.bookings, // <-- use 'bookings'
                backgroundColor: "rgba(54, 162, 235, 0.6)"
            }]
        },
        options: { indexAxis: "y", responsive: true, plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true } } }
    });

    // 2️⃣ Revenue per Lot (Horizontal Bar)
    const revenueData = await fetchData("http://127.0.0.1:5000/admin/stats/revenue_per_lot");
    const ctxRevenue = document.getElementById("chartRevenue").getContext("2d");
    new Chart(ctxRevenue, {
        type: "bar",
        data: {
            labels: revenueData.lots,       // <-- use 'lots'
            datasets: [{
                label: "Revenue (₹)",
                data: revenueData.revenue,  // <-- use 'revenue'
                backgroundColor: "rgba(255, 99, 132, 0.6)"
            }]
        },
        options: { indexAxis: "y", responsive: true, plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true } } }
    });

    // 3️⃣ User vs Bookings (Vertical Bar)
    const userBookingsData = await fetchData("http://127.0.0.1:5000/admin/stats/bookings_per_user"); // <-- route fixed
    const ctxUserBooking = document.getElementById("chartUserBooking").getContext("2d");
    new Chart(ctxUserBooking, {
        type: "bar",
        data: {
            labels: userBookingsData.users,       // <-- use 'users'
            datasets: [{
                label: "Number of Bookings",
                data: userBookingsData.bookings,  // <-- use 'bookings'
                backgroundColor: "rgba(75, 192, 192, 0.6)"
            }]
        },
        options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
    });
}

// Initialize charts
renderCharts();
