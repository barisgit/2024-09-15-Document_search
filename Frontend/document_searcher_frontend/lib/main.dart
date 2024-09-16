import 'package:flutter/material.dart';
import 'document_searcher.dart';

void main() {
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Document Searcher',
      theme: ThemeData(
        primarySwatch: Colors.blue,
        visualDensity: VisualDensity.adaptivePlatformDensity,
      ),
      home: Scaffold(
        body: DocumentSearcher(),
      ),
      builder: (context, child) {
        return ScrollConfiguration(
          behavior: ScrollBehavior(),
          child: GestureDetector(
            onTap: () {
              FocusScope.of(context).requestFocus(FocusNode());
            },
            child: child!,
          ),
        );
      },
    );
  }
}