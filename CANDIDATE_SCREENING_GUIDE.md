# Candidate Screening Guide - Technical Assessment Framework

## Purpose
This guide helps you systematically evaluate software engineering candidates for the TTB platform migration project. Use this during interviews and technical assessments.

---

## Pre-Interview Screening Checklist

### Portfolio Review (15 minutes)
Review candidate's GitHub and portfolio before scheduling interview.

**Green Flags** (1 point each):
- [ ] GitHub profile shows consistent activity (50+ commits in past year)
- [ ] Has contributed to open-source projects in Python or JavaScript
- [ ] Portfolio includes 2+ SaaS or data platform projects
- [ ] Code examples show clean structure, documentation, and tests
- [ ] Projects demonstrate full-stack capabilities (backend + frontend)
- [ ] README files are comprehensive and well-written
- [ ] Commits have clear, descriptive messages

**Red Flags** (disqualify):
- [ ] No GitHub profile or portfolio provided
- [ ] Code samples are poorly structured or undocumented
- [ ] No evidence of production experience with required tech stack
- [ ] Portfolio only shows tutorial projects or bootcamp assignments

**Minimum to Proceed**: 4+ green flags, zero red flags

---

## Initial Screening Call (15-20 minutes)

### Introduction Questions (5 minutes)
1. **Tell me about your most complex SaaS project. What was your role?**
   - Look for: Full-stack responsibility, production deployment, user scale
   - Red flag: Only worked on small pieces, never owned a feature end-to-end

2. **What's your experience with our core tech stack? (Python Flask, React/Vue, PostgreSQL)**
   - Look for: 2+ years with each technology, production experience
   - Red flag: "I can learn it" or "I've used similar technologies"

### Technical Depth Questions (10 minutes)

#### Database Experience
**Question**: "Walk me through a time you migrated a database or dealt with a database performance issue."

**What to listen for**:
- Specific technologies and versions
- Understanding of indexes, query optimization, migration strategies
- Consideration of downtime, data integrity, rollback plans
- Actual metrics (response time improvements, query performance)

**Strong answer example**:
"I migrated a Rails app from MySQL to PostgreSQL. We had 500GB of data and couldn't have downtime. I set up logical replication, ran dual writes for 2 weeks to verify data consistency, then switched over with only 30 seconds of read-only mode. After migration, we optimized indexes and reduced average query time from 850ms to 120ms."

**Weak answer example**:
"I've used PostgreSQL before. It's pretty straightforward to migrate data. You just export and import."

#### Authentication & Security
**Question**: "How would you implement user authentication for a multi-tenant SaaS application?"

**What to listen for**:
- JWT vs session-based authentication (should mention both pros/cons)
- Token refresh strategies
- Password hashing (bcrypt, Argon2)
- Multi-tenancy data isolation
- OWASP security concerns

**Strong answer**:
"I'd use JWT with refresh tokens. Access tokens expire in 15 minutes, refresh tokens in 7 days. Store refresh tokens in httpOnly cookies to prevent XSS. For multi-tenancy, I'd use a tenant_id claim in the JWT and enforce it at the database query level with row-level security in PostgreSQL. All passwords hashed with bcrypt cost factor 12."

**Weak answer**:
"Just use JWT tokens. Pretty standard stuff."

#### Frontend Architecture
**Question**: "Our app has 8 pages with shared components like navigation, modals, and data tables. How would you structure a React application for this?"

**What to listen for**:
- Component hierarchy and reusability
- State management strategy (Context API, Redux, Zustand)
- Code splitting and lazy loading
- Shared UI component library
- API data fetching patterns

**Strong answer**:
"I'd create a shared component library for navigation, modals, tables, buttons, etc. Use React Context for app-wide state (user auth, theme) and React Query for server state management. Implement lazy loading for each route. Structure would be: /components (shared UI), /features (page-specific logic), /hooks (custom hooks), /services (API calls), /utils (helpers)."

**Weak answer**:
"Just create components for each page and reuse them where needed."

### Project Fit Questions (5 minutes)

1. **"What would you prioritize in the first 2 weeks if you started today?"**
   - Strong answer: Mentions database migration planning, authentication setup, understanding current architecture
   - Weak answer: "Whatever you need me to do" or jumps into coding without planning

2. **"You discover the current codebase has 1,200 lines in a single app.py file with no tests. What's your approach?"**
   - Strong answer: Incremental refactoring, add tests for critical paths first, don't break existing functionality
   - Weak answer: "Rewrite everything from scratch" or "That's really bad, I'd fix it immediately"

3. **"How do you handle working with a codebase you didn't write?"**
   - Strong answer: Spend time understanding architecture, ask questions, document as I go, respect existing patterns
   - Weak answer: "I'd probably just rewrite the parts I need to work on"

### Logistics & Commitment (3 minutes)
1. When can you start?
2. Can you commit 30-40 hours/week for the first 2 months?
3. What time zone are you in? Can you overlap 4+ hours with US Eastern Time?
4. What's your hourly rate or fixed-price proposal for Phase 1?

**Decision Point**: Proceed to technical interview if:
- Strong answers to 2+ technical questions
- Availability and rate align with budget
- Genuine interest in the project (not just looking for any gig)

---

## Technical Interview (60-90 minutes)

### Part 1: Deep Dive on Experience (20 minutes)

#### Database Migration Project
**Ask**: "Tell me about the most complex database work you've done. What were the challenges?"

**Evaluation criteria** (3 points each):
- [ ] Has migrated production databases with real user impact
- [ ] Understands indexing strategies and query optimization
- [ ] Considers data integrity and rollback procedures
- [ ] Mentions monitoring and alerting for database performance
- [ ] Discusses connection pooling, replication, or scaling strategies

**Minimum score to proceed**: 9/15

#### Multi-Tenant SaaS Architecture
**Ask**: "Describe a multi-tenant system you've built or worked on. How did you handle data isolation?"

**Evaluation criteria** (3 points each):
- [ ] Explains schema-based vs database-based tenancy trade-offs
- [ ] Discusses security implications and data isolation strategies
- [ ] Mentions tenant-specific configuration and customization
- [ ] Considers billing, usage tracking, and resource limits
- [ ] Talks about deployment and scaling for multiple tenants

**Minimum score to proceed**: 9/15

### Part 2: System Design Exercise (25 minutes)

**Scenario**: "We need to enrich 10,000 brands with contact information from Apollo.io API. The API has rate limits (50 requests/minute) and costs $1 per contact. Design a system to process this efficiently."

**What to listen for**:

1. **Requirements Clarification** (should ask questions):
   - How quickly do we need results?
   - Can it run in the background?
   - What happens if the API call fails?
   - Do we need to retry failed enrichments?
   - How do users track progress?

2. **System Design** (should mention):
   - Job queue system (Celery, RQ, or similar)
   - Rate limiting strategy (token bucket, leaky bucket)
   - Retry logic with exponential backoff
   - Database schema for tracking job status
   - Webhook or polling for user notifications
   - Cost tracking and limits

3. **Error Handling** (should consider):
   - API failures and timeouts
   - Invalid brand data
   - Rate limit exceeded
   - Budget exhausted (cost cap)

**Strong answer structure**:
```
1. Use Celery with Redis as message broker
2. Create enrichment_jobs table (status, progress, cost, created_at)
3. Queue processor respects 50 req/min limit with token bucket
4. Exponential backoff for failures (1s, 2s, 4s, 8s)
5. WebSocket updates for real-time progress
6. Admin dashboard to monitor costs and pause jobs
7. Comprehensive logging for debugging
```

**Scoring** (5 points each):
- [ ] Mentions background job processing
- [ ] Addresses rate limiting properly
- [ ] Includes retry logic
- [ ] Considers cost tracking
- [ ] Provides user feedback mechanism
- [ ] Discusses error handling and monitoring

**Minimum score to proceed**: 20/30

### Part 3: Code Quality Discussion (15 minutes)

**Show candidate a simplified version of your current code**:

```python
# Example from current codebase (simplified)
@app.route('/enrich_brand', methods=['POST'])
def enrich_brand():
    data = request.get_json()
    brand_name = data['brand_name']

    # Search for brand website
    results = search_engine.search(brand_name)

    # Update database
    conn = sqlite3.connect('brands.db')
    cursor = conn.cursor()
    cursor.execute(f"UPDATE brands SET url = '{results[0]}' WHERE name = '{brand_name}'")
    conn.commit()
    conn.close()

    return {'status': 'success'}
```

**Ask**: "What issues do you see with this code? How would you improve it?"

**What they should identify** (2 points each):
- [ ] SQL injection vulnerability (f-string in query)
- [ ] No error handling (what if search fails? no results?)
- [ ] No input validation (brand_name could be None or empty)
- [ ] Direct database access in route (should use service layer)
- [ ] No logging for debugging
- [ ] Hardcoded database path
- [ ] No transaction rollback on error
- [ ] Should return proper HTTP status codes
- [ ] No authentication/authorization check
- [ ] Blocking operation (should be async/background job)

**Minimum identified issues**: 6/10

**Ask for improved version**. Strong answer example:
```python
@app.route('/enrich_brand', methods=['POST'])
@require_auth
@rate_limit(10, per=60)  # 10 requests per minute
def enrich_brand():
    try:
        data = request.get_json()

        # Validate input
        brand_name = data.get('brand_name', '').strip()
        if not brand_name:
            return {'error': 'brand_name is required'}, 400

        # Use service layer
        enrichment_service = EnrichmentService(db)
        result = enrichment_service.enrich_brand(brand_name)

        # Queue background job instead of blocking
        job = celery_app.send_task('tasks.enrich_brand', args=[brand_name])

        logger.info(f"Enrichment queued for brand: {brand_name}",
                   extra={'job_id': job.id, 'user_id': current_user.id})

        return {
            'status': 'queued',
            'job_id': job.id,
            'message': 'Enrichment started'
        }, 202

    except Exception as e:
        logger.error(f"Enrichment failed: {str(e)}", exc_info=True)
        return {'error': 'Internal server error'}, 500
```

### Part 4: Architecture Discussion (15 minutes)

**Present your current architecture** (show file structure from CLAUDE.md)

**Ask**: "Looking at our current structure, what concerns do you have? What would you change first?"

**Strong answers should mention**:
- Monolithic app.py needs refactoring into blueprints/routers
- Missing tests directory and test coverage
- No clear separation between business logic and data access
- Database connections should be managed by connection pool
- Missing requirements.txt or dependency management
- No configuration management for different environments
- Missing CI/CD configuration files

**Ask follow-up**: "If you had 2 weeks, what's your refactoring plan?"

**Strong answer structure**:
1. Week 1: Add tests to critical paths, set up CI/CD, create service layer
2. Week 2: Extract blueprints, implement proper database session management
3. Document architecture decisions and create migration guide
4. Don't break existing functionality - incremental improvement

**Weak answer**:
"I'd rewrite everything in FastAPI/Django/Next.js because it's better."

### Part 5: Problem-Solving Exercise (15 minutes)

**Scenario**: "Users report that the /brands page is slow, taking 8-12 seconds to load. It displays 100 brands per page from a table with 38,596 brands. How would you debug and fix this?"

**What to listen for**:

1. **Debugging approach** (should mention):
   - Check database query performance (EXPLAIN ANALYZE)
   - Profile the endpoint (cProfile, Flask-DebugToolbar)
   - Check network tab for API response times
   - Look at database indexes
   - Review pagination implementation

2. **Potential issues** (should identify):
   - Missing indexes on sort/filter columns
   - N+1 query problem (loading related data)
   - Loading too much data (SELECT *)
   - No query result caching
   - Inefficient JSON serialization

3. **Solutions** (should propose):
   - Add database indexes
   - Use pagination properly (LIMIT/OFFSET or cursor-based)
   - Cache query results for common filters
   - Optimize SELECT to only needed columns
   - Use database views for complex queries
   - Add API response compression

**Scoring** (5 points each):
- [ ] Systematic debugging approach
- [ ] Mentions database query optimization
- [ ] Considers caching strategies
- [ ] Proposes multiple solutions
- [ ] Discusses trade-offs of each approach

**Minimum score**: 15/25

---

## Code Review Exercise (Take-Home, 2-3 hours)

Send candidate a small PR from your codebase (200-300 lines) and ask them to:
1. Review the code as if they were on your team
2. Provide written feedback on GitHub (or similar)
3. Suggest at least 3 specific improvements

**Evaluation criteria**:

### Code Review Quality (30 points total)
- [ ] Identifies security issues (5 points)
- [ ] Suggests readability improvements (5 points)
- [ ] Points out error handling gaps (5 points)
- [ ] Recommends testing strategies (5 points)
- [ ] Considers performance implications (5 points)
- [ ] Provides actionable feedback (not vague) (5 points)

### Communication Style
- [ ] Professional and constructive tone
- [ ] Explains *why* changes are needed
- [ ] Provides code examples for suggestions
- [ ] Prioritizes feedback (critical vs nice-to-have)

**Red flags**:
- Nitpicky formatting comments without substance
- Rude or dismissive tone
- Missing obvious security or logic issues
- Only identifies problems, doesn't suggest solutions

**Minimum score to proceed**: 20/30

---

## Reference Check Questions

For 1-2 references provided by candidate:

1. **"What was [candidate]'s role on your project? What did they own?"**
   - Look for: End-to-end ownership, leadership, technical decisions

2. **"How was their code quality? Did they write tests and documentation?"**
   - Look for: High standards, maintainable code, good documentation

3. **"How did they handle ambiguity or changing requirements?"**
   - Look for: Adaptability, problem-solving, communication

4. **"Did they require a lot of direction or could they work independently?"**
   - Look for: Self-direction, proactive communication

5. **"Would you hire them again? Why or why not?"**
   - Look for: Enthusiastic yes with specific reasons

6. **"On a scale of 1-10, how would you rate their technical abilities?"**
   - Look for: 8+ rating

7. **"Were there any areas where they struggled or needed improvement?"**
   - Look for: Honest assessment, growth mindset

**Red flags**:
- Lukewarm recommendation ("They were fine...")
- Can't provide specific examples
- Mentions reliability or communication issues
- Wouldn't hire again

---

## Final Scoring Rubric

### Technical Skills (50 points)
- Database expertise: ___/10
- Backend development: ___/10
- Frontend development: ___/10
- System design: ___/10
- Code quality: ___/10

### Problem-Solving (25 points)
- Debugging approach: ___/10
- Architectural thinking: ___/10
- Code review quality: ___/5

### Communication & Fit (25 points)
- Clear communication: ___/10
- Work style alignment: ___/5
- Cultural fit: ___/5
- References: ___/5

### Total Score: ___/100

**Hiring Decision Matrix**:
- **90-100**: Strong hire - Make offer immediately
- **75-89**: Good hire - Make offer with slightly lower rate or probation period
- **60-74**: Maybe hire - Consider if desperate, but set clear improvement expectations
- **Below 60**: Do not hire - Keep searching

---

## Interview Questions Bank

### Additional Technical Questions

#### Python/Flask Specific
1. "Explain the difference between Flask blueprints and application factories. When would you use each?"
2. "How do you handle database sessions in Flask? What's the difference between scoped_session and regular session?"
3. "How would you implement rate limiting in a Flask API?"

#### Database
1. "Explain the difference between database indexes and what types exist (B-tree, hash, GiST, etc.)"
2. "How would you handle a table with 10 million rows that needs daily updates?"
3. "What's your approach to database migrations in production with zero downtime?"

#### Frontend
1. "Explain React's virtual DOM. Why is it faster than direct DOM manipulation?"
2. "How do you prevent prop drilling in React? Compare Context API vs Redux."
3. "What's your approach to API error handling in the frontend?"

#### DevOps
1. "Walk me through your ideal CI/CD pipeline for a Flask application."
2. "How do you handle environment-specific configuration (dev, staging, prod)?"
3. "Explain Docker multi-stage builds and why you'd use them."

#### Security
1. "What are the OWASP Top 10? How would you prevent each in our application?"
2. "Explain JWT security best practices. What are common vulnerabilities?"
3. "How do you prevent SQL injection in a Python application?"

### Behavioral Questions

1. **Handling Pressure**: "Tell me about a time you had to deliver a critical feature under a tight deadline. How did you manage?"

2. **Technical Disagreement**: "Describe a time you disagreed with a technical decision. How did you handle it?"

3. **Debugging Complex Issues**: "Tell me about the most challenging bug you've fixed. How did you approach it?"

4. **Learning New Technology**: "Describe a time you had to quickly learn a new technology or framework to complete a project."

5. **Code Quality vs Speed**: "Tell me about a time you had to balance moving fast with maintaining code quality. What did you do?"

---

## Red Flags to Watch For

### During Conversation
- Talks negatively about previous employers/clients
- Blames others for project failures
- Overly confident without substance ("I know everything about React")
- Can't explain technical decisions they've made
- Avoids questions about failures or challenges

### In Code/Portfolio
- No tests in any project
- Poor documentation or no README files
- Copy-pasted code from tutorials without understanding
- Incomplete projects with no explanation why
- No commit history (bulk commits of finished code)

### Communication Style
- Doesn't ask clarifying questions
- Gives vague answers without specifics
- Talks over you or doesn't listen
- Can't explain complex topics simply
- Defensive when given feedback

### Work Style Concerns
- Not available during agreed-upon hours
- Slow to respond to messages
- Makes excuses for incomplete work
- Doesn't proactively communicate blockers
- Needs extensive hand-holding for basic tasks

---

## Onboarding Checklist (If Hired)

Once you've hired a candidate, use this checklist:

### Week 1: Setup & Context
- [ ] GitHub repository access
- [ ] Development environment setup guide
- [ ] Access to staging environment
- [ ] Slack/communication channel access
- [ ] Review codebase and architecture docs
- [ ] Review CLAUDE.md for project context
- [ ] 1-hour kick-off call to align on priorities

### Week 2-4: First Contributions
- [ ] Complete one small bug fix (get familiar with process)
- [ ] Submit first feature PR (authentication or database migration)
- [ ] Daily async standup updates
- [ ] Weekly video sync (30 minutes)

### Success Metrics (First Month)
- [ ] 2+ meaningful PRs merged
- [ ] Code passes review with minimal revisions
- [ ] Proactive communication about blockers
- [ ] Demonstrates understanding of architecture
- [ ] On track for Phase 1 milestones

---

## Questions to Ask Candidates

Let them ask you questions. Strong candidates will ask about:
- Technical challenges and architecture decisions
- Team structure and collaboration style
- Product roadmap and priorities
- Success metrics and expectations
- Code review process
- Deployment and release cycle

Weak candidates will only ask about:
- Pay, hours, and logistics
- "What will I be working on?" (should have read the job posting)
- No questions at all

---

*Use this guide as a framework, not a script. Adapt based on the conversation and candidate's background.*
