import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * BankQueueServer.java
 * High-performance standalone Java REST API server for https://queue-wiz-home.lovable.app
 * Zero external dependencies. Runs directly on Java 11 / 17 / 18 / 21:
 * Command: java BankQueueServer.java
 */
public class BankQueueServer {

    private static final int PORT = 8080;

    // In-memory data models
    static class ServiceItem {
        int id;
        String code;
        String name;
        String description;
        String estimatedTime;
        int durationMinutes;
        String prefix;
        String icon;

        ServiceItem(int id, String code, String name, String description, String estimatedTime, int durationMinutes, String prefix, String icon) {
            this.id = id;
            this.code = code;
            this.name = name;
            this.description = description;
            this.estimatedTime = estimatedTime;
            this.durationMinutes = durationMinutes;
            this.prefix = prefix;
            this.icon = icon;
        }

        String toJson() {
            return String.format(
                "{\"id\":%d,\"code\":\"%s\",\"name\":\"%s\",\"description\":\"%s\",\"estimated_time\":\"%s\",\"duration_minutes\":%d,\"prefix\":\"%s\",\"icon\":\"%s\",\"is_active\":true}",
                id, escapeJson(code), escapeJson(name), escapeJson(description), escapeJson(estimatedTime), durationMinutes, prefix, icon
            );
        }
    }

    static class CounterItem {
        int id;
        String name;
        String deskLabel;
        String description;
        String status;
        String staffName;
        String currentTokenNumber;

        CounterItem(int id, String name, String deskLabel, String description, String status, String staffName, String currentTokenNumber) {
            this.id = id;
            this.name = name;
            this.deskLabel = deskLabel;
            this.description = description;
            this.status = status;
            this.staffName = staffName;
            this.currentTokenNumber = currentTokenNumber;
        }

        String toJson(int waitingCount) {
            String tokenJson = currentTokenNumber == null ? "null" : "\"" + escapeJson(currentTokenNumber) + "\"";
            return String.format(
                "{\"id\":%d,\"name\":\"%s\",\"desk_label\":\"%s\",\"description\":\"%s\",\"status\":\"%s\",\"staff_name\":\"%s\",\"current_token_number\":%s,\"waiting_count\":%d}",
                id, escapeJson(name), escapeJson(deskLabel), escapeJson(description), escapeJson(status), escapeJson(staffName), tokenJson, waitingCount
            );
        }
    }

    static class TokenItem {
        int id;
        String tokenNumber;
        int serviceId;
        int counterId;
        String customerName;
        String customerPhone;
        String customerEmail;
        String customerAccountNumber;
        String bookingDate;
        String timeSlot;
        String status; // WAITING, APPROACHING, SERVING, COMPLETED
        int estimatedWaitMinutes;
        String recommendedArrivalTime;
        LocalDateTime createdAt;

        TokenItem(int id, String tokenNumber, int serviceId, int counterId, String customerName, String customerPhone,
                  String customerEmail, String customerAccountNumber, String bookingDate, String timeSlot,
                  String status, int estimatedWaitMinutes, String recommendedArrivalTime) {
            this.id = id;
            this.tokenNumber = tokenNumber;
            this.serviceId = serviceId;
            this.counterId = counterId;
            this.customerName = customerName;
            this.customerPhone = customerPhone;
            this.customerEmail = customerEmail;
            this.customerAccountNumber = customerAccountNumber;
            this.bookingDate = bookingDate;
            this.timeSlot = timeSlot;
            this.status = status;
            this.estimatedWaitMinutes = estimatedWaitMinutes;
            this.recommendedArrivalTime = recommendedArrivalTime;
            this.createdAt = LocalDateTime.now();
        }

        String toJson(String serviceName, String counterName, String deskLabel, int peopleAhead) {
            return String.format(
                "{\"id\":%d,\"token_number\":\"%s\",\"service_id\":%d,\"service_name\":\"%s\",\"customer_name\":\"%s\",\"customer_phone\":\"%s\",\"customer_account_number\":%s,\"booking_date\":\"%s\",\"time_slot\":\"%s\",\"status\":\"%s\",\"counter_id\":%d,\"counter_name\":\"%s\",\"desk_label\":\"%s\",\"people_ahead\":%d,\"estimated_wait_minutes\":%d,\"recommended_arrival_time\":\"%s\",\"created_at\":\"%s\"}",
                id, tokenNumber, serviceId, escapeJson(serviceName), escapeJson(customerName), escapeJson(customerPhone),
                customerAccountNumber == null ? "null" : "\"" + escapeJson(customerAccountNumber) + "\"",
                escapeJson(bookingDate), escapeJson(timeSlot), status, counterId, escapeJson(counterName), escapeJson(deskLabel),
                peopleAhead, estimatedWaitMinutes, escapeJson(recommendedArrivalTime), createdAt.toString()
            );
        }
    }

    // State Store
    private static final Map<Integer, ServiceItem> services = new LinkedHashMap<>();
    private static final Map<Integer, CounterItem> counters = new LinkedHashMap<>();
    private static final List<TokenItem> tokens = new CopyOnWriteArrayList<>();
    private static final List<String> recentUpdates = new CopyOnWriteArrayList<>();
    private static final AtomicInteger tokenSeq = new AtomicInteger(109);

    static {
        // Initialize Services
        services.put(1, new ServiceItem(1, "DEP", "Cash Deposit", "Deposit cash safely into your account.", "8 min", 8, "A", "banknote"));
        services.put(2, new ServiceItem(2, "WTH", "Cash Withdrawal", "Withdraw cash with assisted counter service.", "10 min", 10, "A", "credit-card"));
        services.put(3, new ServiceItem(3, "ACC", "Account Opening", "Open a new savings or current account.", "25 min", 25, "B", "wallet-cards"));
        services.put(4, new ServiceItem(4, "PBK", "Passbook Update", "Update and print your latest transactions.", "5 min", 5, "D", "file-text"));
        services.put(5, new ServiceItem(5, "CHQ", "Cheque Services", "Cheque deposit, clearing and related support.", "12 min", 12, "C", "check-square"));
        services.put(6, new ServiceItem(6, "CRD", "ATM / Debit Card", "Card issue, replacement and PIN assistance.", "15 min", 15, "C", "credit-card"));
        services.put(7, new ServiceItem(7, "OTH", "Other Services", "General customer service and inquiries.", "15 min", 15, "B", "help-circle"));

        // Initialize Counters
        counters.put(1, new CounterItem(1, "Counter 1", "Cash services", "Cash deposit and withdrawal", "BUSY", "Ramesh Kumar", "A104"));
        counters.put(2, new CounterItem(2, "Counter 2", "Account Services", "New accounts and KYC", "BUSY", "Priya Sharma", "B201"));
        counters.put(3, new CounterItem(3, "Counter 3", "Cheque & Card Desk", "Cheque clearance & debit cards", "ONLINE", "Vikram Singh", null));
        counters.put(4, new CounterItem(4, "Counter 4", "Quick Services & Passbook", "Passbook updates", "ONLINE", "Sneha Patel", null));

        // Initial Demo Tokens
        tokens.add(new TokenItem(1, "A104", 1, 1, "Ananya Rao", "+919876500104", null, null, "Today", "10:15 AM", "SERVING", 0, "10:15 AM"));
        tokens.add(new TokenItem(2, "A105", 1, 1, "Karthik Verma", "+919876500105", null, null, "Today", "10:30 AM", "APPROACHING", 8, "10:25 AM"));
        tokens.add(new TokenItem(3, "A106", 2, 1, "Siddharth Jain", "+919876500106", null, null, "Today", "10:45 AM", "WAITING", 18, "10:40 AM"));
        tokens.add(new TokenItem(4, "A108", 1, 1, "Meera Patel", "+919876500108", "meera@example.com", "48920193821", "Today", "10:30 AM", "APPROACHING", 12, "10:20 AM"));
        tokens.add(new TokenItem(5, "B201", 3, 2, "Arjun Menon", "+919876500201", null, null, "Today", "10:00 AM", "SERVING", 0, "10:00 AM"));
        tokens.add(new TokenItem(6, "C102", 5, 3, "Neha Gupta", "+919876500302", null, null, "Today", "11:00 AM", "WAITING", 15, "10:50 AM"));

        recentUpdates.add("Your token A108 is approaching. Please plan to arrive soon.");
        recentUpdates.add("Your estimated wait changed by 5 minutes.");
        recentUpdates.add("A108 was successfully reserved for 10:30 AM.");
    }

    public static void main(String[] args) throws IOException {
        HttpServer server = HttpServer.create(new InetSocketAddress(PORT), 0);

        server.createContext("/health", new HealthHandler());
        server.createContext("/api/v1/services", new ServicesHandler());
        server.createContext("/api/v1/counters", new CountersHandler());
        server.createContext("/api/v1/queue/live", new LiveQueueHandler());
        server.createContext("/api/v1/tokens/book", new TokenBookHandler());
        server.createContext("/api/v1/tokens/track/", new TokenTrackHandler());
        server.createContext("/api/v1/contact", new ContactHandler());
        server.createContext("/", new RootHandler());

        server.setExecutor(null);
        System.out.println("============================================================");
        System.out.println(" Bank Queue Management System — Java API Server");
        System.out.println(" Serving frontend at: https://queue-wiz-home.lovable.app");
        System.out.println(" Java Server running on http://127.0.0.1:" + PORT);
        System.out.println(" Healthcheck: http://127.0.0.1:" + PORT + "/health");
        System.out.println(" Live Queue:  http://127.0.0.1:" + PORT + "/api/v1/queue/live");
        System.out.println(" Services:    http://127.0.0.1:" + PORT + "/api/v1/services");
        System.out.println("============================================================");
        server.start();
    }

    // CORS and response helpers
    private static void sendJsonResponse(HttpExchange exchange, int statusCode, String responseJson) throws IOException {
        exchange.getResponseHeaders().set("Content-Type", "application/json; charset=UTF-8");
        exchange.getResponseHeaders().set("Access-Control-Allow-Origin", "*");
        exchange.getResponseHeaders().set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS");
        exchange.getResponseHeaders().set("Access-Control-Allow-Headers", "Content-Type, Authorization");

        if ("OPTIONS".equalsIgnoreCase(exchange.getRequestMethod())) {
            exchange.sendResponseHeaders(204, -1);
            return;
        }

        byte[] bytes = responseJson.getBytes(StandardCharsets.UTF_8);
        exchange.sendResponseHeaders(statusCode, bytes.length);
        try (OutputStream os = exchange.getResponseBody()) {
            os.write(bytes);
        }
    }

    private static String escapeJson(String s) {
        if (s == null) return "";
        return s.replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\b", "\\b")
                .replace("\f", "\\f")
                .replace("\n", "\\n")
                .replace("\r", "\\r")
                .replace("\t", "\\t");
    }

    // Handlers
    static class HealthHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            sendJsonResponse(exchange, 200, "{\"status\":\"healthy\",\"service\":\"Bank Queue Java API\",\"connected_frontend\":\"https://queue-wiz-home.lovable.app\"}");
        }
    }

    static class ServicesHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            StringBuilder sb = new StringBuilder("[");
            int count = 0;
            for (ServiceItem s : services.values()) {
                if (count > 0) sb.append(",");
                sb.append(s.toJson());
                count++;
            }
            sb.append("]");
            sendJsonResponse(exchange, 200, sb.toString());
        }
    }

    static class CountersHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            StringBuilder sb = new StringBuilder("[");
            int count = 0;
            for (CounterItem c : counters.values()) {
                int waiting = (int) tokens.stream()
                        .filter(t -> t.counterId == c.id && ("WAITING".equals(t.status) || "APPROACHING".equals(t.status)))
                        .count();
                if (count > 0) sb.append(",");
                sb.append(c.toJson(waiting));
                count++;
            }
            sb.append("]");
            sendJsonResponse(exchange, 200, sb.toString());
        }
    }

    static class LiveQueueHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            long totalWaiting = tokens.stream().filter(t -> "WAITING".equals(t.status) || "APPROACHING".equals(t.status)).count();
            long totalServed = tokens.stream().filter(t -> "COMPLETED".equals(t.status)).count();

            // Counters JSON
            StringBuilder countersSb = new StringBuilder("[");
            int cCount = 0;
            for (CounterItem c : counters.values()) {
                int waiting = (int) tokens.stream().filter(t -> t.counterId == c.id && ("WAITING".equals(t.status) || "APPROACHING".equals(t.status))).count();
                if (cCount > 0) countersSb.append(",");
                countersSb.append(c.toJson(waiting));
                cCount++;
            }
            countersSb.append("]");

            // Now Serving JSON
            StringBuilder servingSb = new StringBuilder("[");
            int sCount = 0;
            for (CounterItem c : counters.values()) {
                if (c.currentTokenNumber != null) {
                    if (sCount > 0) servingSb.append(",");
                    servingSb.append(String.format("{\"token_number\":\"%s\",\"counter_name\":\"%s\",\"desk_label\":\"%s\"}",
                            escapeJson(c.currentTokenNumber), escapeJson(c.name), escapeJson(c.deskLabel)));
                    sCount++;
                }
            }
            servingSb.append("]");

            // Recent updates
            StringBuilder updatesSb = new StringBuilder("[");
            for (int i = 0; i < recentUpdates.size(); i++) {
                if (i > 0) updatesSb.append(",");
                updatesSb.append(String.format("{\"id\":\"up-%d\",\"text\":\"%s\",\"timestamp\":\"10:30 AM\"}", i + 1, escapeJson(recentUpdates.get(i))));
            }
            updatesSb.append("]");

            String json = String.format(
                "{\"total_waiting\":%d,\"total_served_today\":%d,\"active_counters_count\":%d,\"average_wait_minutes\":12,\"counters\":%s,\"now_serving\":%s,\"upcoming_tokens\":[],\"recent_updates\":%s}",
                totalWaiting, totalServed, counters.size(), countersSb.toString(), servingSb.toString(), updatesSb.toString()
            );
            sendJsonResponse(exchange, 200, json);
        }
    }

    static class TokenTrackHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            String path = exchange.getRequestURI().getPath();
            String tokenNumber = path.substring(path.lastIndexOf('/') + 1).toUpperCase().trim();

            TokenItem found = tokens.stream().filter(t -> t.tokenNumber.equalsIgnoreCase(tokenNumber)).findFirst().orElse(null);
            if (found == null) {
                sendJsonResponse(exchange, 404, "{\"detail\":\"Token not found\"}");
                return;
            }

            ServiceItem s = services.get(found.serviceId);
            CounterItem c = counters.get(found.counterId);

            long ahead = tokens.stream().filter(t -> t.serviceId == found.serviceId && ("WAITING".equals(t.status) || "APPROACHING".equals(t.status)) && t.id < found.id).count();

            String notice;
            if ("SERVING".equals(found.status)) {
                notice = "Your token " + found.tokenNumber + " is now being served at " + (c != null ? c.name : "Counter") + ". Please proceed immediately.";
            } else if ("APPROACHING".equals(found.status) || ahead <= 2) {
                notice = "Your token " + found.tokenNumber + " is approaching. Please plan to arrive soon.";
            } else {
                notice = "Your token " + found.tokenNumber + " is scheduled for " + found.timeSlot + ".";
            }

            String json = String.format(
                "{\"token_number\":\"%s\",\"service_name\":\"%s\",\"customer_name\":\"%s\",\"status\":\"%s\",\"counter_name\":\"%s\",\"desk_label\":\"%s\",\"people_ahead\":%d,\"estimated_wait_minutes\":%d,\"recommended_arrival_time\":\"%s\",\"notice\":\"%s\",\"booking_date\":\"%s\",\"time_slot\":\"%s\"}",
                found.tokenNumber, s != null ? escapeJson(s.name) : "Service", escapeJson(found.customerName),
                found.status, c != null ? escapeJson(c.name) : "Counter 1", c != null ? escapeJson(c.deskLabel) : "General Desk",
                ahead, ahead * (s != null ? s.durationMinutes : 10), escapeJson(found.recommendedArrivalTime),
                escapeJson(notice), escapeJson(found.bookingDate), escapeJson(found.timeSlot)
            );
            sendJsonResponse(exchange, 200, json);
        }
    }

    static class TokenBookHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if ("OPTIONS".equalsIgnoreCase(exchange.getRequestMethod())) {
                sendJsonResponse(exchange, 204, "");
                return;
            }

            String body = new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);

            // Simple json field extraction
            String name = extractStringField(body, "customer_name", "Customer");
            String phone = extractStringField(body, "customer_phone", "+919876543210");
            int serviceId = extractIntField(body, "service_id", 1);
            String date = extractStringField(body, "booking_date", "Today");
            String slot = extractStringField(body, "time_slot", "10:30 AM");

            ServiceItem s = services.getOrDefault(serviceId, services.get(1));
            int nextNum = tokenSeq.incrementAndGet();
            String tokenNum = s.prefix + nextNum;

            int counterId = 1;
            if ("B".equals(s.prefix)) counterId = 2;
            else if ("C".equals(s.prefix)) counterId = 3;
            else if ("D".equals(s.prefix)) counterId = 4;

            CounterItem c = counters.get(counterId);

            TokenItem newToken = new TokenItem(
                tokens.size() + 1, tokenNum, s.id, counterId, name, phone, null, null, date, slot, "WAITING", 16, "10:15 AM"
            );
            tokens.add(newToken);
            recentUpdates.add(0, tokenNum + " was successfully reserved for " + slot + ".");

            String json = newToken.toJson(s.name, c != null ? c.name : "Counter 1", c != null ? c.deskLabel : "Desk", 2);
            sendJsonResponse(exchange, 200, json);
        }
    }

    static class ContactHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            sendJsonResponse(exchange, 200, "{\"success\":true,\"message\":\"Thank you for reaching out! Our branch team has received your message.\"}");
        }
    }

    static class RootHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            exchange.getResponseHeaders().set("Content-Type", "text/html; charset=UTF-8");
            exchange.getResponseHeaders().set("Access-Control-Allow-Origin", "*");
            String html = "<html><body style='font-family:sans-serif;padding:2rem;'><h1>Bank Queue Java API Server</h1><p>Active and serving for <b>queue-wiz-home.lovable.app</b></p><ul><li><a href='/api/v1/services'>/api/v1/services</a></li><li><a href='/api/v1/counters'>/api/v1/counters</a></li><li><a href='/api/v1/queue/live'>/api/v1/queue/live</a></li><li><a href='/api/v1/tokens/track/A108'>/api/v1/tokens/track/A108</a></li></ul></body></html>";
            byte[] b = html.getBytes(StandardCharsets.UTF_8);
            exchange.sendResponseHeaders(200, b.length);
            try (OutputStream os = exchange.getResponseBody()) { os.write(b); }
        }
    }

    private static String extractStringField(String json, String field, String defVal) {
        String key = "\"" + field + "\"";
        int idx = json.indexOf(key);
        if (idx == -1) return defVal;
        int colon = json.indexOf(':', idx);
        int startQuote = json.indexOf('"', colon);
        int endQuote = json.indexOf('"', startQuote + 1);
        if (startQuote != -1 && endQuote != -1) {
            return json.substring(startQuote + 1, endQuote);
        }
        return defVal;
    }

    private static int extractIntField(String json, String field, int defVal) {
        String key = "\"" + field + "\"";
        int idx = json.indexOf(key);
        if (idx == -1) return defVal;
        int colon = json.indexOf(':', idx);
        int end = json.indexOf(',', colon);
        if (end == -1) end = json.indexOf('}', colon);
        if (end != -1) {
            try {
                return Integer.parseInt(json.substring(colon + 1, end).trim());
            } catch (Exception ignored) {}
        }
        return defVal;
    }
}
