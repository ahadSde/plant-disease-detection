package edu.vit.plantdisease.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.vit.plantdisease.model.ChatMessage;
import edu.vit.plantdisease.model.Diagnosis;
import edu.vit.plantdisease.repository.ChatMessageRepository;
import edu.vit.plantdisease.repository.DiagnosisRepository;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;
import java.io.IOException;
import java.nio.file.*;
import java.util.*;
import java.util.stream.Collectors;

@Service
public class DiagnosisService {
    private static final long MAX_IMAGE_BYTES = 15L * 1024 * 1024;
    private static final Set<String> IMAGE_TYPES = Set.of("image/jpeg", "image/png", "image/webp");
    private final DiagnosisRepository diagnoses;
    private final ChatMessageRepository messages;
    private final AiServiceClient ai;
    private final ObjectMapper json;
    private final Path uploadDirectory;

    public DiagnosisService(DiagnosisRepository diagnoses, ChatMessageRepository messages, AiServiceClient ai,
                           ObjectMapper json, @Value("${app.upload-dir}") String uploadDirectory) {
        this.diagnoses = diagnoses; this.messages = messages; this.ai = ai; this.json = json;
        this.uploadDirectory = Paths.get(uploadDirectory).toAbsolutePath().normalize();
    }

    @Transactional
    public Map<String, Object> create(String sessionId, MultipartFile image) {
        validateImage(image);
        String extension = extension(image.getContentType());
        String filename = UUID.randomUUID() + extension;
        Path stored = uploadDirectory.resolve(filename).normalize();
        if (!stored.startsWith(uploadDirectory)) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Invalid image filename.");
        try {
            byte[] imageBytes = image.getBytes();
            Files.createDirectories(uploadDirectory);
            Files.write(stored, imageBytes, StandardOpenOption.CREATE_NEW);
            MediaType mediaType = MediaType.parseMediaType(image.getContentType());
            Map<String, Object> result = ai.diagnose(imageBytes, filename, mediaType);
            Map<String, Object> prediction = objectMap(result.get("prediction"));
            Map<String, Object> retrieval = objectMap(result.get("retrieval"));
            Map<String, Object> advisory = objectMap(result.get("advisory"));

            Diagnosis diagnosis = new Diagnosis();
            diagnosis.setSessionId(sessionId);
            diagnosis.setImageUrl("/images/" + filename);
            diagnosis.setDiseaseClass(Objects.toString(prediction.get("disease_class"), "Unknown"));
            diagnosis.setConfidence(number(prediction.get("confidence")));
            diagnosis.setExplanation(Objects.toString(advisory.get("answer"), "No advisory was returned."));
            diagnosis.setRemedy(Objects.toString(advisory.get("answer"), ""));
            diagnosis.setRetrievalStatus(Objects.toString(advisory.getOrDefault("status", retrieval.get("status")), "unknown"));
            diagnosis.setAdvisorySessionId(Objects.toString(advisory.get("session_id"), null));
            diagnosis.setSourcesJson(json.writeValueAsString(advisory.getOrDefault("sources", List.of())));
            diagnoses.save(diagnosis);
            String initialAnswer = diagnosis.getExplanation();
            messages.save(new ChatMessage(diagnosis, "assistant", initialAnswer));
            return diagnosisView(diagnosis, List.of(new ChatMessageView("assistant", initialAnswer, diagnosis.getCreatedAt())));
        } catch (AiServiceUnavailableException error) {
            deleteQuietly(stored);
            throw error;
        } catch (IOException error) {
            deleteQuietly(stored);
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "Could not store the image or read the AI response.", error);
        } catch (RuntimeException error) {
            deleteQuietly(stored);
            throw error;
        }
    }

    @Transactional(readOnly = true)
    public List<Map<String, Object>> history(String sessionId) {
        return diagnoses.findAllBySessionIdOrderByCreatedAtDesc(sessionId).stream()
            .map(d -> diagnosisView(d, List.of())).collect(Collectors.toList());
    }

    @Transactional(readOnly = true)
    public Map<String, Object> get(String sessionId, UUID id) {
        Diagnosis diagnosis = owned(sessionId, id);
        List<ChatMessageView> thread = messages.findAllByDiagnosisIdOrderByTimestampAsc(id).stream()
            .map(m -> new ChatMessageView(m.getSender(), m.getMessage(), m.getTimestamp())).toList();
        return diagnosisView(diagnosis, thread);
    }

    @Transactional
    public Map<String, Object> ask(String sessionId, UUID id, String question) {
        if (question == null || question.isBlank() || question.length() > 4000)
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Enter a question of 1–4,000 characters.");
        Diagnosis diagnosis = owned(sessionId, id);
        String answer;
        List<Map<String, Object>> sources = readSources(diagnosis);
        if (!"ok".equals(diagnosis.getRetrievalStatus())) {
            answer = "No verified reference is available for this diagnosis, so I cannot provide a grounded answer yet. Please consult a qualified local agricultural extension service.";
        } else {
            Map<String, Object> response = ai.followUp(diagnosis.getAdvisorySessionId(), question);
            answer = Objects.toString(response.get("answer"), "The advisory service returned no answer.");
            sources = mapList(response.get("sources"));
        }
        messages.save(new ChatMessage(diagnosis, "user", question));
        messages.save(new ChatMessage(diagnosis, "assistant", answer));
        return Map.of("sender", "assistant", "message", answer, "timestamp", java.time.Instant.now(), "sources", sources);
    }

    @Transactional(readOnly = true)
    public Path imagePath(String filename) {
        if (filename == null || !filename.matches("[a-fA-F0-9-]+\\.(jpg|png|webp)"))
            throw new ResponseStatusException(HttpStatus.NOT_FOUND);
        Path path = uploadDirectory.resolve(filename).normalize();
        if (!path.startsWith(uploadDirectory) || !Files.isRegularFile(path)) throw new ResponseStatusException(HttpStatus.NOT_FOUND);
        return path;
    }

    private Diagnosis owned(String sessionId, UUID id) {
        return diagnoses.findByIdAndSessionId(id, sessionId)
            .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Diagnosis not found."));
    }
    private void validateImage(MultipartFile image) {
        if (image == null || image.isEmpty()) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Choose an image first.");
        if (image.getSize() > MAX_IMAGE_BYTES) throw new ResponseStatusException(HttpStatus.PAYLOAD_TOO_LARGE, "Image must be 15 MB or smaller.");
        if (!IMAGE_TYPES.contains(image.getContentType())) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Use a JPEG, PNG, or WebP image.");
    }
    private static String extension(String mime) { return switch (mime) { case "image/png" -> ".png"; case "image/webp" -> ".webp"; default -> ".jpg"; }; }
    private static double number(Object value) { return value instanceof Number n ? n.doubleValue() : 0.0; }
    @SuppressWarnings("unchecked") private static Map<String, Object> objectMap(Object value) { return value instanceof Map<?, ?> map ? (Map<String, Object>) map : Map.of(); }
    @SuppressWarnings("unchecked") private static List<Map<String, Object>> mapList(Object value) { return value instanceof List<?> list ? (List<Map<String, Object>>) list : List.of(); }
    private List<Map<String, Object>> readSources(Diagnosis d) {
        try { return json.readValue(d.getSourcesJson() == null ? "[]" : d.getSourcesJson(), new TypeReference<>() {}); }
        catch (IOException ignored) { return List.of(); }
    }
    private Map<String, Object> diagnosisView(Diagnosis d, List<ChatMessageView> thread) {
        Map<String, Object> view = new LinkedHashMap<>();
        view.put("id", d.getId()); view.put("imageUrl", d.getImageUrl()); view.put("diseaseClass", d.getDiseaseClass());
        view.put("confidence", d.getConfidence()); view.put("explanation", d.getExplanation()); view.put("remedy", d.getRemedy());
        view.put("retrievalStatus", d.getRetrievalStatus()); view.put("sources", readSources(d)); view.put("createdAt", d.getCreatedAt());
        view.put("messages", thread);
        return view;
    }
    private static void deleteQuietly(Path path) { try { Files.deleteIfExists(path); } catch (IOException ignored) {} }
    public record ChatMessageView(String sender, String message, java.time.Instant timestamp) {}
}
