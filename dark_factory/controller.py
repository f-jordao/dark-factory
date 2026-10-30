import json

from .models import eligibility, review_key, same_revision, validate_result


class Controller:
    def __init__(self, github, state, policy, reviewer):
        self.github, self.state = github, state
        self.policy, self.reviewer = policy, reviewer

    def reconcile(self, number, execute=False, publish=False, retry=False):
        snapshot = self.github.snapshot(number)
        reason = eligibility(snapshot, self.policy)
        self.state.observe(snapshot, reason)
        response = {
            "repo": snapshot.repo, "pr": number, "head": snapshot.head,
            "base": snapshot.base, "review_invocations": 0,
        }
        if reason != "eligible":
            return dict(response, action="stopped" if reason == "closed" else "waiting", reason=reason)
        key = review_key(snapshot, self.policy)
        response["review_key"] = key
        row = self.state.get(key)
        if row and row["status"] in ("published", "stale"):
            return dict(response, action=row["status"])
        needs_review = row is None or row["status"] in ("running", "failed", "blocked")
        if needs_review:
            if not execute:
                return dict(response, action="would_review" if row is None else row["status"])
            owner = self.state.claim_review(key, snapshot, self.policy, retry=retry)
            if owner is None:
                return dict(response, action=self.state.get(key)["status"])
            try:
                packet = self.github.packet(snapshot, self.policy.max_patch_bytes)
                current = self.github.snapshot(number)
                if not same_revision(snapshot, current) or eligibility(current, self.policy) != "eligible":
                    self.state.finish_review(
                        key, owner, error="Eligibility changed before review", started=False
                    )
                    return dict(response, action="waiting", reason="changed_before_review")
                response["review_invocations"] = 1
                result = validate_result(self.reviewer.review(key, packet), packet)
            except Exception as error:
                self.state.finish_review(
                    key, owner, error=str(error), started=response["review_invocations"] > 0
                )
                raise
            self.state.finish_review(key, owner, result=result)
            row = self.state.get(key)
        if not publish:
            return dict(response, action=row["status"])
        owner = self.state.claim_publication(key)
        if owner is None:
            return dict(response, action=self.state.get(key)["status"])
        try:
            current = self.github.snapshot(number)
            if not same_revision(snapshot, current) or current.state != "open":
                self.state.finish_publication(key, owner, stale=True)
                return dict(response, action="stale")
            if eligibility(current, self.policy) != "eligible":
                self.state.finish_publication(key, owner, error="Eligibility changed before publication")
                return dict(response, action="waiting", reason="changed_before_publication")
            result = json.loads(self.state.get(key)["result"])
            existing = self.github.find_published_review(snapshot, key)
            review_id = existing if existing is not None else self.github.publish(snapshot, key, result)
            self.state.finish_publication(key, owner, review_id=review_id)
            return dict(response, action="published", review_id=review_id)
        except Exception as error:
            self.state.finish_publication(key, owner, error=str(error))
            raise
