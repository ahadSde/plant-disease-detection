package edu.vit.plantdisease.controller;

import edu.vit.plantdisease.service.AiServiceUnavailableException;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.server.ResponseStatusException;
import java.util.Map;

@RestControllerAdvice
public class ApiExceptionHandler {
    @ExceptionHandler(AiServiceUnavailableException.class)
    public org.springframework.http.ResponseEntity<Map<String, String>> aiUnavailable(AiServiceUnavailableException error) {
        return org.springframework.http.ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
            .body(Map.of("error", error.getMessage()));
    }
    @ExceptionHandler(ResponseStatusException.class)
    public org.springframework.http.ResponseEntity<Map<String, String>> status(ResponseStatusException error) {
        return org.springframework.http.ResponseEntity.status(error.getStatusCode())
            .body(Map.of("error", error.getReason() == null ? "Request failed." : error.getReason()));
    }
}
