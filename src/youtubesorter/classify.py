# Process videos
processed, failed, skipped = common.process_videos(
    self.youtube,
    self.source_playlist,
    self.filter_prompt,
    self.target_playlist,
    copy=True,
    verbose=self.verbose
)

# Log results
if processed:
    logger.info("Moved %d videos to target playlist", len(processed)) 