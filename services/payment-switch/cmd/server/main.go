package main

import (
	"encoding/json"
	"log"
	"net/http"
	"sync"
	"time"

	"github.com/google/uuid"
)

type Payment struct {
	ID           string  `json:"id"`
	SenderID     string  `json:"sender_id"`
	ReceiverID   string  `json:"receiver_id"`
	Amount       float64 `json:"amount"`
	Currency     string  `json:"currency"`
	Status       string  `json:"status"`
	CreatedAt    time.Time `json:"created_at"`
	CompletedAt  *time.Time `json:"completed_at,omitempty"`
}

type PaymentRequest struct {
	SenderID   string  `json:"sender_id"`
	ReceiverID string  `json:"receiver_id"`
	Amount     float64 `json:"amount"`
	Currency   string  `json:"currency"`
}

type PaymentResponse struct {
	ID string `json:"id"`
}

var (
	payments = sync.Map{}
)

func main() {
	http.HandleFunc("/health", healthHandler)
	http.HandleFunc("/v1/payments", paymentsHandler)
	http.HandleFunc("/v1/payments/", paymentStatusHandler)

	log.Println("Starting payment router on port 8080")
	if err := http.ListenAndServe(":8080", nil); err != nil {
		log.Fatal(err)
	}
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}

func paymentsHandler(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case "POST":
		handleCreatePayment(w, r)
	case "GET":
		handleGetPayments(w, r)
	default:
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
}

func handleCreatePayment(w http.ResponseWriter, r *http.Request) {
	var req PaymentRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	if req.SenderID == "" || req.ReceiverID == "" || req.Amount <= 0 || req.Currency == "" {
		http.Error(w, "Invalid payment request", http.StatusBadRequest)
		return
	}

	paymentID := uuid.New().String()
	payment := Payment{
		ID:         paymentID,
		SenderID:   req.SenderID,
		ReceiverID: req.ReceiverID,
		Amount:     req.Amount,
		Currency:   req.Currency,
		Status:     "processing",
		CreatedAt:  time.Now(),
	}

	payments.Store(paymentID, payment)

	// Publish event to stdout (structured log)
	event := map[string]interface{}{
		"event": "payment_created",
		"id":    paymentID,
		"timestamp": time.Now().Unix(),
		"payload": map[string]interface{}{
			"sender_id":   req.SenderID,
			"receiver_id": req.ReceiverID,
			"amount":      req.Amount,
			"currency":    req.Currency,
			"status":      "processing",
		},
	}
	log.Println("EVENT:", event)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(PaymentResponse{ID: paymentID})
}

func handleGetPayments(w http.ResponseWriter, r *http.Request) {
	// This endpoint would list all payments if needed
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{"message": "Listing all payments", "count": 0})
}

func paymentStatusHandler(w http.ResponseWriter, r *http.Request) {
	// Extract ID from the URL path
	id := r.URL.Path[len("/v1/payments/"):]
	
	if id == "" {
		http.Error(w, "Payment ID required", http.StatusBadRequest)
		return
	}

	if val, ok := payments.Load(id); ok {
		payment := val.(Payment)
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(payment)
	} else {
		http.Error(w, "Payment not found", http.StatusNotFound)
	}
}