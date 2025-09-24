package main

import (
	"io"
	"log"
	"log/slog"
	"net"
	"net/http"
	"os"
	"time"
)

// Main handler
func handleProxy(w http.ResponseWriter, r *http.Request) {
	// Auth first
	if !checkAuth(r) {
		w.Header().Set("Proxy-Authenticate", `Basic realm="Restricted"`)
		http.Error(w, "Proxy Authentication Required", http.StatusProxyAuthRequired)
		return
	}

	if r.Method == http.MethodConnect {
		handleTunneling(w, r)
	} else {
		handleHTTP(w, r)
	}
}

// Very simple auth check (Basic Auth)
func checkAuth(r *http.Request) bool {
	// Look for Proxy-Authorization header
	auth := r.Header.Get("Proxy-Authorization")
	if auth == "" {
		return false
	}

	// Reuse Go's parsing logic by making a fake request
	req := &http.Request{Header: http.Header{"Authorization": []string{auth}}}

	username, password, ok := req.BasicAuth()
	if !ok {
		return false
	}

	// Get expected credentials from the environment
	expectedUser := os.Getenv("PROXY_USER")
	expectedPass := os.Getenv("PROXY_PASS")

	return username == expectedUser && password == expectedPass
}

// Handle HTTPS tunneling (CONNECT)
func handleTunneling(w http.ResponseWriter, r *http.Request) {
	destConn, err := net.DialTimeout("tcp", r.Host, 10*time.Second)
	if err != nil {
		http.Error(w, err.Error(), http.StatusServiceUnavailable)

		return
	}

	defer callAndLogError(destConn.Close)

	// Write 200 Connection Established to the client
	w.WriteHeader(http.StatusOK)

	// Hijack the connection to get the raw TCP stream
	hijacker, ok := w.(http.Hijacker)
	if !ok {
		http.Error(w, "Hijacking not supported", http.StatusInternalServerError)

		return
	}

	clientConn, _, err := hijacker.Hijack()
	if err != nil {
		http.Error(w, err.Error(), http.StatusServiceUnavailable)

		return
	}

	defer callAndLogError(clientConn.Close)

	// Bidirectional copy between client and destination
	go func() {
		_, err = io.Copy(destConn, clientConn)
		if err != nil {
			slog.Error(err.Error())
		}
	}()

	_, err = io.Copy(clientConn, destConn)
	if err != nil {
		slog.Error(err.Error())
	}
}

// HTTP proxy handler
func handleHTTP(w http.ResponseWriter, r *http.Request) {
	// Create a new request based on the incoming one
	outReq, err := http.NewRequest(r.Method, r.RequestURI, r.Body)
	if err != nil {
		http.Error(w, "Error creating request", http.StatusInternalServerError)

		return
	}

	outReq.Header = r.Header.Clone()

	// Use http.DefaultTransport to perform the request
	resp, err := http.DefaultTransport.RoundTrip(outReq)
	if err != nil {
		http.Error(w, "Error forwarding request: "+err.Error(), http.StatusBadGateway)

		return
	}

	defer callAndLogError(resp.Body.Close)

	// Copy response headers
	for key, values := range resp.Header {
		for _, value := range values {
			w.Header().Add(key, value)
		}
	}

	// Write status code
	w.WriteHeader(resp.StatusCode)

	// Copy body
	_, err = io.Copy(w, resp.Body)
	if err != nil {
		slog.Error(err.Error())
	}
}

func callAndLogError(f func() error) {
	if err := f(); err != nil {
		slog.Error(err.Error())
	}
}

func main() {
	server := &http.Server{
		Addr:    ":8080", // listen on port 8080
		Handler: http.HandlerFunc(handleProxy),
	}

	// Check if port is available
	ln, err := net.Listen("tcp", server.Addr)
	if err != nil {
		log.Fatalf("Could not listen on %s: %v", server.Addr, err)
	}

	log.Printf("Proxy server listening on %s", server.Addr)

	if err = server.Serve(ln); err != nil {
		log.Fatalf("Server failed: %v", err)
	}
}
