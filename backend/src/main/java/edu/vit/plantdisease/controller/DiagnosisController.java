package edu.vit.plantdisease.controller;

import edu.vit.plantdisease.service.DiagnosisService;
import edu.vit.plantdisease.service.AiServiceClient;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import org.springframework.core.io.FileSystemResource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import java.nio.file.Path;
import java.util.*;

@RestController
@RequestMapping("/api")
public class DiagnosisController {
    private final DiagnosisService diagnoses;
    private final AiServiceClient ai;
    public DiagnosisController(DiagnosisService diagnoses, AiServiceClient ai) { this.diagnoses = diagnoses; this.ai = ai; }

    @GetMapping("/health")
    public Map<String, Object> health() { return Map.of("status", "ok", "aiService", ai.health().getOrDefault("status", "unknown")); }

    @PostMapping(value = "/diagnoses", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public Map<String, Object> create(@RequestHeader("X-Session-Id") String sessionId,
                                      @RequestPart("image") MultipartFile image) {
        return diagnoses.create(validSession(sessionId), image);
    }

    @GetMapping("/diagnoses")
    public List<Map<String, Object>> history(@RequestHeader("X-Session-Id") String sessionId) {
        return diagnoses.history(validSession(sessionId));
    }

    @GetMapping("/diagnoses/{id}")
    public Map<String, Object> get(@RequestHeader("X-Session-Id") String sessionId, @PathVariable UUID id) {
        return diagnoses.get(validSession(sessionId), id);
    }

    @PostMapping("/diagnoses/{id}/messages")
    public Map<String, Object> ask(@RequestHeader("X-Session-Id") String sessionId,
                                  @PathVariable UUID id, @Valid @RequestBody MessageRequest request) {
        return diagnoses.ask(validSession(sessionId), id, request.message());
    }

    @GetMapping("/images/{filename:.+}")
    public ResponseEntity<FileSystemResource> image(@PathVariable String filename) {
        Path path = diagnoses.imagePath(filename);
        String name = path.getFileName().toString().toLowerCase(Locale.ROOT);
        MediaType type = name.endsWith(".png") ? MediaType.IMAGE_PNG
            : name.endsWith(".webp") ? MediaType.parseMediaType("image/webp") : MediaType.IMAGE_JPEG;
        return ResponseEntity.ok().header(HttpHeaders.CACHE_CONTROL, "private, max-age=86400")
            .contentType(type).body(new FileSystemResource(path));
    }

    private static String validSession(String raw) {
        try { return UUID.fromString(raw).toString(); }
        catch (RuntimeException error) { throw new org.springframework.web.server.ResponseStatusException(org.springframework.http.HttpStatus.BAD_REQUEST, "X-Session-Id must be a UUID."); }
    }

    public record MessageRequest(@NotBlank String message) {}
}
