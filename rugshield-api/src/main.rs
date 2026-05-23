use axum::{
    extract::Path,
    response::Json,
    routing::get,
    Router,
};
use serde::{Deserialize, Serialize};
use std::net::SocketAddr;
use tower_http::cors::CorsLayer;

#[derive(Serialize, Deserialize)]
struct Signal {
    id: u32,
    name: String,
    weight: u32,
    triggered: bool,
}

#[derive(Serialize, Deserialize)]
struct ScoreResponse {
    mint: String,
    score: u32,
    #[serde(rename = "riskLevel")]
    risk_level: String,
    signals: Vec<Signal>,
    timestamp: u64,
}

async fn get_score(Path(mint_address): Path<String>) -> Json<ScoreResponse> {
    // MOCK DATA - Replace with real P2 scoring later
    let mock_response = ScoreResponse {
        mint: mint_address,
        score: 75,
        risk_level: "HIGH".to_string(),
        signals: vec![
            Signal {
                id: 1,
                name: "Mint Authority Not Revoked".to_string(),
                weight: 20,
                triggered: true,
            },
            Signal {
                id: 2,
                name: "Freeze Authority Active".to_string(),
                weight: 8,
                triggered: false,
            },
            Signal {
                id: 3,
                name: "Upgradeable Contract".to_string(),
                weight: 10,
                triggered: true,
            },
        ],
        timestamp: std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs(),
    };

    Json(mock_response)
}

async fn health_check() -> &'static str {
    "RugShield API is running"
}

#[tokio::main]
async fn main() {
    let app = Router::new()
        .route("/health", get(health_check))
        .route("/score/:mint", get(get_score))
        .layer(CorsLayer::permissive());

    let addr = SocketAddr::from(([0, 0, 0, 0], 3000));
    println!("🚀 RugShield API listening on http://localhost:3000");

    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}
