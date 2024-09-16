import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:io';

class DocumentSearcher extends StatefulWidget {
  @override
  _DocumentSearcherState createState() => _DocumentSearcherState();
}

class _DocumentSearcherState extends State<DocumentSearcher> {
  final TextEditingController _searchController = TextEditingController();
  List<dynamic> _searchResults = [];
  bool _isLoading = false;
  String _baseUrl = '';

  @override
  void initState() {
    super.initState();
    _initializeBaseUrl();
  }

  Future<void> _initializeBaseUrl() async {
    String host = 'localhost';
    if (Platform.isAndroid) {
      host = '10.0.2.2';
    } else if (Platform.isIOS) {
      try {
        for (var interface in await NetworkInterface.list()) {
          for (var addr in interface.addresses) {
            if (addr.type == InternetAddressType.IPv4) {
              host = addr.address;
              break;
            }
          }
          if (host != 'localhost') break;
        }
      } catch (e) {
        print('Error getting network interfaces: $e');
      }
    }
    setState(() {
      _baseUrl = 'http://$host:8000';
    });
    print('Base URL set to: $_baseUrl');
  }

  Future<void> _performSearch() async {
    if (_baseUrl.isEmpty) {
      print('Base URL is not set yet. Initializing...');
      await _initializeBaseUrl();
    }

    setState(() {
      _isLoading = true;
    });

    try {
      print('Sending request to: $_baseUrl/search');
      final response = await http.post(
        Uri.parse('$_baseUrl/search'),
        headers: <String, String>{
          'Content-Type': 'application/json; charset=UTF-8',
        },
        body: jsonEncode(<String, String>{
          'query': _searchController.text,
        }),
      );

      print('Response status: ${response.statusCode}');
      print('Response body: ${response.body}');

      if (response.statusCode == 200) {
        setState(() {
          _searchResults = jsonDecode(response.body);
          _isLoading = false;
        });
      } else {
        throw Exception('Failed to load search results');
      }
    } catch (e) {
      print('Error performing search: $e');
      setState(() {
        _isLoading = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('An error occurred while searching. Please try again.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Document Searcher'),
      ),
      body: Column(
        children: <Widget>[
          Padding(
            padding: const EdgeInsets.all(8.0),
            child: TextField(
              controller: _searchController,
              decoration: InputDecoration(
                labelText: 'Search',
                suffixIcon: IconButton(
                  icon: Icon(Icons.search),
                  onPressed: _performSearch,
                ),
              ),
            ),
          ),
          Expanded(
            child: _isLoading
                ? Center(child: CircularProgressIndicator())
                : ListView.builder(
                    itemCount: _searchResults.length,
                    itemBuilder: (context, index) {
                      final result = _searchResults[index];
                      return ListTile(
                        title: Text(result['filename']),
                        subtitle: Text(result['path']),
                        trailing: Chip(label: Text(result['language'])),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}