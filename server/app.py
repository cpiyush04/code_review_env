def main():
    import uvicorn
    from openenv.core.env_server.http_server import create_app
    from code_review.models import CodeReviewAction, CodeReviewObservation
    from code_review.server.code_review_environment import CodeReviewEnvironment

    app = create_app(
        CodeReviewEnvironment,
        CodeReviewAction,
        CodeReviewObservation,
        env_name="code_review",
        max_concurrent_envs=1,
    )
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()