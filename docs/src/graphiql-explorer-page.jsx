import React, { Component } from "react";
import { render } from "react-dom";
import { buildClientSchema, getIntrospectionQuery, parse } from "graphql";
import GraphiQL from "graphiql";
import GraphiQLExplorer from "graphiql-explorer";
import "graphiql/graphiql.css";
import "./static/css/app.css"
import "./static/css/graphiql.css"

const getGQLEndpoint = function() {
  const res = /service=([^&]+)/.exec(location.search);
  if (res && res.length == 2) {
    return `https://${res[1]}.dipdup.net/v1/graphql`;
  } else {
    return 'https://metadata.dipdup.net/v1/graphql';
  }
}

const fetcher = params => {
  return fetch(
    getGQLEndpoint(),
    {
      method: 'post',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(params),
      credentials: 'omit',
    },
  ).then(response => {
      return response.text();
    })
    .then(responseBody => {
      try {
        return JSON.parse(responseBody);
      } catch (e) {
        return responseBody;
      }
    });
};

const ZERO_INFO_PATIENCE_MS = 1500;

class App extends Component {
  constructor(props) {
    super(props);
    this._graphiql = GraphiQL;
    this.state = {
      schema: null,
      loading_schema: false,
      query: '',
      explorerIsOpen: true
    };
  }

  componentDidMount() {
    document.getElementById("endpoint").innerText = getGQLEndpoint();
    setTimeout(() => {
      if (this.state.schema === null) {
        this.setState({
          loading_schema: true,
        });
      }
    }, ZERO_INFO_PATIENCE_MS);
    fetcher({
      query: getIntrospectionQuery()
    }).then(result => {
      this.setState({
        schema: buildClientSchema(result.data),
        loading_schema: false,
      });
    });
  }

  _handleEditQuery = query => {
    this.setState({ query });
  };

  _handleToggleExplorer = () => {
    this.setState({ explorerIsOpen: !this.state.explorerIsOpen });
  };

  render() {
    const { query, schema } = this.state;
    return (
      <div className="graphiql-container">
        { this.state.loading_schema &&
          <p className="loading-informer">
            Schema is loading
          </p>
        }
        <GraphiQLExplorer
          schema={schema}
          query={query}
          onEdit={this._handleEditQuery}
          onRunOperation={operationName =>
            this._graphiql.handleRunQuery(operationName)
          }
          explorerIsOpen={this.state.explorerIsOpen}
          onToggleExplorer={this._handleToggleExplorer}
        />
        <GraphiQL
          fetcher={fetcher}
          schema={schema}
          query={query}
          onEditQuery={this._handleEditQuery}
          docExplorerOpen={false}
        >
          <GraphiQL.Toolbar>
            <GraphiQL.Button
              onClick={() => this._graphiql.handlePrettifyQuery()}
              label="Prettify"
              title="Prettify Query"
            />
            <GraphiQL.Button
              onClick={() => this._graphiql.handleToggleHistory()}
              label="History"
              title="Show History"
            />
            <GraphiQL.Button
              onClick={this._handleToggleExplorer}
              label="Explorer"
              title="Toggle Explorer"
            />
          </GraphiQL.Toolbar>
        </GraphiQL>
      </div>
    );
  }
}

render(<App />, document.getElementById("graphiql"));