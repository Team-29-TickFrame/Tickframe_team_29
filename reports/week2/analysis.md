## Learning points

During Week 2, the team learned how to identify stakeholders and transform customer needs into structured user stories.
Using the MoSCoW prioritization method helped us distinguish between essential MVP functionality and features that can be postponed to future releases.
We learned that authentication and guest access are both important user journeys. While registered users require personalized functionality, visitors should be able to explore the platform before creating an account.
The prototyping process helped us understand how market analysts interact with live market data, detected patterns, and signal feeds. Creating interface mockups allowed us to validate navigation flows and ensure that key information is accessible from a single dashboard.
The team also learned the importance of including empty, success, and error states to improve user experience.

## Validated assumptions

We assumed that market analysts need a centralized dashboard where they can monitor market data, detected patterns, and signals in real time.
This assumption was validated during prototype development because combining market overview and asset analysis into a single dashboard reduced navigation complexity.
We also assumed that users would benefit from guest access before registration. This assumption was confirmed because it lowers the entry barrier and allows visitors to explore the platform before creating an account.
Another validated assumption was that pattern detection results should be displayed directly on charts together with confidence scores, making them easier to interpret.

## Needs clarification

Several questions remain open for future iterations:

- Which cryptocurrency exchanges will be supported beyond the MVP.
- How confidence scores for pattern detection should be calculated.
- What refresh interval should be used for live market data.
- Whether guest users should have restricted access to certain features.
- What authentication provider and security requirements should be used in production.

Technical risks include exchange API reliability, data normalization across multiple exchanges, and real-time processing performance.

## Planned response

For MVP v1, the team will focus on implementing the following user stories:

- US-01 Secure login
- US-02 Guest access
- US-03 Live market data visualization
- US-04 Automatic chart pattern detection
- US-05 Live signal feed

The validated dashboard prototype will be used as the primary interface for MVP v1.

Future iterations may expand functionality with historical analytics, correlation analysis, advanced alerting, and system monitoring capabilities.
