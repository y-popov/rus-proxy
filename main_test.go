package main

import (
	"bytes"
	"encoding/base64"
	"errors"
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestHandleRequestAndRedirect(t *testing.T) {
	tests := []struct {
		name           string
		requestMethod  string
		requestBody    string
		requestHeaders map[string]string
		mockResponse   *http.Response
		mockError      error
		expectedCode   int
		expectedBody   string
		dropCreds      bool
	}{
		{
			name:          "successful http request",
			requestMethod: http.MethodGet,
			mockResponse: &http.Response{
				StatusCode: http.StatusOK,
				Body:       io.NopCloser(bytes.NewBufferString("success")),
			},
			expectedCode: http.StatusOK,
			expectedBody: "success",
		},
		{
			name:          "bad gateway on forward error",
			requestMethod: http.MethodGet,
			mockError:     errors.New("dial tcp connection failed"),
			expectedCode:  http.StatusBadGateway,
			expectedBody:  "Error forwarding request: dial tcp connection failed\n",
		},
		{
			name:          "request with wrong credentials",
			requestMethod: http.MethodGet,
			expectedCode:  http.StatusProxyAuthRequired,
			expectedBody:  "Proxy Authentication Required\n",
			dropCreds:     true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			originalTransport := http.DefaultTransport
			defer func() { http.DefaultTransport = originalTransport }()

			http.DefaultTransport = &mockTransport{
				response: tt.mockResponse,
				err:      tt.mockError,
			}

			req := httptest.NewRequest(tt.requestMethod, "/test", bytes.NewBufferString(tt.requestBody))
			for k, v := range tt.requestHeaders {
				req.Header.Add(k, v)
			}

			if !tt.dropCreds {
				req.Header.Add(
					"Proxy-Authorization",
					"Basic "+base64.StdEncoding.EncodeToString([]byte("test-user:valid-pass")),
				)
			}

			rr := httptest.NewRecorder()

			t.Setenv("PROXY_USER", "test-user")
			t.Setenv("PROXY_PASS", "valid-pass")

			handleProxy(rr, req)

			res := rr.Result()

			t.Cleanup(callAndLogCleanup(t, res.Body.Close))

			if res.StatusCode != tt.expectedCode {
				t.Errorf("expected status %d, got %d", tt.expectedCode, res.StatusCode)
			}

			body, _ := io.ReadAll(res.Body)
			if string(body) != tt.expectedBody {
				t.Errorf("expected body %q, got %q", tt.expectedBody, string(body))
			}

			if tt.mockResponse != nil {
				for key, values := range tt.mockResponse.Header {
					for _, value := range values {
						if rr.Header().Get(key) != value {
							t.Errorf("expected header %q with value %q, got %q", key, value, rr.Header().Get(key))
						}
					}
				}
			}
		})
	}
}

type mockTransport struct {
	response *http.Response
	err      error
}

func (m *mockTransport) RoundTrip(_ *http.Request) (*http.Response, error) {
	return m.response, m.err
}

func callAndLogCleanup(t *testing.T, f func() error) func() {
	t.Helper()

	return func() {
		if err := f(); err != nil {
			t.Log(err)
		}
	}
}

// Start a simple TCP echo server
func startEchoServer(t *testing.T) (addr string, closeFn func()) {
	ln, err := net.Listen("tcp", "127.0.0.1:0") // random free port
	if err != nil {
		t.Fatal(err)
	}

	go func() {
		for {
			conn, err := ln.Accept()
			if err != nil {
				return
			}

			go func(c net.Conn) {
				defer callAndLogError(c.Close)

				_, err = io.Copy(c, c) // echo back
				if err != nil {
					t.Error(err)
				}
			}(conn)
		}
	}()

	return ln.Addr().String(), func() { callAndLogError(ln.Close) }
}

func TestHandleTunneling(t *testing.T) {
	// Start upstream echo server
	targetAddr, closeEcho := startEchoServer(t)
	t.Cleanup(closeEcho)

	// Fake CONNECT request to proxy
	req := httptest.NewRequest(http.MethodConnect, targetAddr, nil)
	w := httptest.NewRecorder()

	// Run tunneling handler
	handleTunneling(w, req)

	// The proxy should reply with 200 (connection established)
	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}
}
