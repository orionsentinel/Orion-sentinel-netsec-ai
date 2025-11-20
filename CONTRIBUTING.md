# Contributing to Orion Sentinel NSM + AI

Thank you for your interest in contributing to Orion Sentinel! This project aims to provide privacy-focused, AI-powered network security monitoring for home and lab environments.

## How to Contribute

### Reporting Issues

If you encounter a bug or have a feature request:

1. Check if the issue already exists in [GitHub Issues](https://github.com/yourusername/orion-sentinel-nsm-ai/issues)
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce (for bugs)
   - Expected vs actual behavior
   - System information (Pi model, OS version, Docker version)
   - Relevant logs or screenshots

### Suggesting Enhancements

We welcome ideas for improvements! When suggesting enhancements:

- Explain the use case and benefits
- Consider how it fits with the project's goals (home/lab security, privacy-focused, Pi-optimized)
- Be specific about what you'd like to see changed or added

### Pull Requests

#### Before You Start

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes
4. Test thoroughly on Raspberry Pi hardware (if possible)

#### Development Guidelines

**Code Style**:
- Python: Follow PEP 8
- Use type hints where appropriate
- Add docstrings to functions and classes
- Keep functions focused and modular

**Configuration**:
- Use environment variables for configuration (via `.env` files)
- Provide sensible defaults
- Document all config options in `.env.example`

**Documentation**:
- Update relevant documentation in `docs/` for significant changes
- Add comments for complex logic
- Update README.md if adding new features

**Testing**:
- Test on actual Raspberry Pi 5 hardware when possible
- Verify Docker containers build and run correctly
- Test with realistic network traffic
- Ensure backward compatibility

**Security**:
- Never commit secrets, API tokens, or credentials
- Use environment variables for sensitive data
- Follow security best practices (least privilege, input validation, etc.)

#### Submitting a Pull Request

1. Commit your changes with clear, descriptive messages
2. Push to your fork: `git push origin feature/your-feature-name`
3. Create a pull request with:
   - Clear title describing the change
   - Description of what changed and why
   - Reference to related issues (if any)
   - Screenshots or logs (if applicable)

4. Respond to review feedback
5. Once approved, your PR will be merged

### Areas for Contribution

We especially welcome contributions in these areas:

#### Documentation
- Tutorials and how-to guides
- Troubleshooting tips
- Grafana dashboard templates
- AI model training guides

#### Features
- New AI models (DGA detection, malware C2, etc.)
- Additional log sources (Zeek, etc.)
- Grafana dashboards
- Alerting integrations (email, Slack, etc.)
- Performance optimizations for Pi

#### Testing
- Unit tests for Python modules
- Integration tests for pipelines
- Performance benchmarks
- Testing on different Pi models

#### Infrastructure
- CI/CD pipelines
- Automated testing
- Docker image optimization
- ARM architecture optimizations

## Development Setup

### Local Development (without Pi)

You can develop and test most features locally without a Raspberry Pi:

```bash
# Clone your fork
git clone https://github.com/yourusername/orion-sentinel-nsm-ai.git
cd orion-sentinel-nsm-ai

# Set up Python virtual environment
cd stacks/ai
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run linters
pip install flake8 mypy
flake8 src/
mypy src/

# Test Python modules
python -m pytest tests/  # (if tests are added)
```

### Testing on Raspberry Pi

For testing the full stack:

1. Set up a Raspberry Pi 5 with fresh OS
2. Follow `docs/pi2-setup.md` for installation
3. Test your changes with real network traffic
4. Monitor resource usage (CPU, RAM, disk)

## Code of Conduct

- Be respectful and constructive
- Welcome newcomers and help them contribute
- Focus on what's best for the project and community
- Accept constructive criticism gracefully

## Questions?

If you have questions about contributing:

- Check existing documentation in `docs/`
- Open a discussion in GitHub Discussions (if enabled)
- Ask in an issue or pull request

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (see [LICENSE](LICENSE)).

---

Thank you for helping make Orion Sentinel better!
