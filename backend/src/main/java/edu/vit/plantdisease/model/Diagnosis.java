package edu.vit.plantdisease.model;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "diagnoses", indexes = {
    @Index(name = "idx_diagnoses_session_created", columnList = "session_id,created_at")
})
public class Diagnosis {
    @Id @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;
    @Column(name = "session_id", nullable = false, length = 36)
    private String sessionId;
    @Column(name = "image_url", nullable = false, length = 500)
    private String imageUrl;
    @Column(name = "disease_class", nullable = false, length = 160)
    private String diseaseClass;
    @Column(nullable = false)
    private double confidence;
    @Column(columnDefinition = "TEXT")
    private String explanation;
    @Column(columnDefinition = "TEXT")
    private String remedy;
    @Column(name = "retrieval_status", nullable = false, length = 80)
    private String retrievalStatus;
    @Column(name = "advisory_session_id", length = 80)
    private String advisorySessionId;
    @Column(name = "sources_json", columnDefinition = "TEXT")
    private String sourcesJson;
    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @PrePersist void onCreate() { if (createdAt == null) createdAt = Instant.now(); }

    public UUID getId() { return id; }
    public String getSessionId() { return sessionId; }
    public void setSessionId(String sessionId) { this.sessionId = sessionId; }
    public String getImageUrl() { return imageUrl; }
    public void setImageUrl(String imageUrl) { this.imageUrl = imageUrl; }
    public String getDiseaseClass() { return diseaseClass; }
    public void setDiseaseClass(String diseaseClass) { this.diseaseClass = diseaseClass; }
    public double getConfidence() { return confidence; }
    public void setConfidence(double confidence) { this.confidence = confidence; }
    public String getExplanation() { return explanation; }
    public void setExplanation(String explanation) { this.explanation = explanation; }
    public String getRemedy() { return remedy; }
    public void setRemedy(String remedy) { this.remedy = remedy; }
    public String getRetrievalStatus() { return retrievalStatus; }
    public void setRetrievalStatus(String retrievalStatus) { this.retrievalStatus = retrievalStatus; }
    public String getAdvisorySessionId() { return advisorySessionId; }
    public void setAdvisorySessionId(String advisorySessionId) { this.advisorySessionId = advisorySessionId; }
    public String getSourcesJson() { return sourcesJson; }
    public void setSourcesJson(String sourcesJson) { this.sourcesJson = sourcesJson; }
    public Instant getCreatedAt() { return createdAt; }
}
