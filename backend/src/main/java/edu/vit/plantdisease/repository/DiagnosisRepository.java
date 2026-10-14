package edu.vit.plantdisease.repository;

import edu.vit.plantdisease.model.Diagnosis;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface DiagnosisRepository extends JpaRepository<Diagnosis, UUID> {
    List<Diagnosis> findAllBySessionIdOrderByCreatedAtDesc(String sessionId);
    Optional<Diagnosis> findByIdAndSessionId(UUID id, String sessionId);
}
