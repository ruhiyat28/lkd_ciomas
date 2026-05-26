import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_theme.dart';
import '../../core/auth/auth_provider.dart';
import '../../core/auth/auth_repository.dart';
import '../../core/api/api_endpoints.dart';
import '../../models/nasabah.dart';

class NasabahListScreen extends ConsumerStatefulWidget {
  const NasabahListScreen({super.key});

  @override
  ConsumerState<NasabahListScreen> createState() => _NasabahListScreenState();
}

class _NasabahListScreenState extends ConsumerState<NasabahListScreen> {
  final _searchCtl = TextEditingController();
  String _status = '';
  String _search = '';
  int _page = 1;
  int _totalPages = 1;
  final List<Nasabah> _allNasabah = [];
  bool _loadingMore = false;
  bool _initialLoading = true;
  final _scrollCtl = ScrollController();

  @override
  void initState() {
    super.initState();
    _scrollCtl.addListener(_onScroll);
    _loadData();
  }

  @override
  void dispose() {
    _searchCtl.dispose();
    _scrollCtl.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_scrollCtl.position.pixels >=
            _scrollCtl.position.maxScrollExtent - 200 &&
        !_loadingMore &&
        _page < _totalPages) {
      _loadMore();
    }
  }

  Future<void> _loadData() async {
    setState(() {
      _page = 1;
      _initialLoading = true;
      _allNasabah.clear();
    });
    await _fetchPage(1);
    if (mounted) setState(() => _initialLoading = false);
  }

  Future<void> _loadMore() async {
    if (_loadingMore) return;
    await _fetchPage(_page + 1);
  }

  Future<void> _fetchPage(int page) async {
    setState(() => _loadingMore = true);
    final api = ref.read(apiClientProvider);
    try {
      final params = <String, dynamic>{
        'page': page,
        'per_page': 20,
        if (_status.isNotEmpty) 'status': _status,
        if (_search.isNotEmpty) 'q': _search,
      };
      final res = await api.get(ApiEndpoints.nasabah, params: params);
      final data = List<Map<String, dynamic>>.from(res.data['data'] ?? []);
      final pag = res.data['pagination'];
      final items = data.map(Nasabah.fromJson).toList();
      if (!mounted) return;
      setState(() {
        _allNasabah.addAll(items);
        _page = pag?['page'] as int? ?? page;
        _totalPages = pag?['pages'] as int? ?? 1;
      });
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
              content: Text('Gagal memuat data'),
              backgroundColor: AppColors.error),
        );
      }
    } finally {
      if (mounted) setState(() => _loadingMore = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authProvider);
    final user = auth.user;

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(title: const Text('Nasabah')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _searchCtl,
                    textInputAction: TextInputAction.search,
                    decoration: const InputDecoration(
                      hintText: 'Cari nama / NIK / ID...',
                      prefixIcon: Icon(Icons.search_rounded),
                      isDense: true,
                    ),
                    onSubmitted: (v) {
                      _search = v.trim();
                      _loadData();
                    },
                  ),
                ),
                const SizedBox(width: 10),
                Container(
                  decoration: BoxDecoration(
                    color: AppColors.surfaceMuted,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  padding: const EdgeInsets.symmetric(horizontal: 10),
                  child: DropdownButtonHideUnderline(
                    child: DropdownButton<String>(
                      value: _status,
                      icon: const Icon(Icons.tune_rounded),
                      items: const [
                        DropdownMenuItem(
                            value: '', child: Text('Semua')),
                        DropdownMenuItem(
                            value: 'aktif', child: Text('Aktif')),
                        DropdownMenuItem(
                            value: 'calon', child: Text('Calon')),
                      ],
                      onChanged: (v) {
                        setState(() => _status = v ?? '');
                        _loadData();
                      },
                    ),
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: _initialLoading
                ? const Center(child: CircularProgressIndicator())
                : RefreshIndicator(
                    onRefresh: _loadData,
                    child: _allNasabah.isEmpty
                        ? ListView(
                            children: const [
                              SizedBox(height: 120),
                              Icon(Icons.people_outline_rounded,
                                  size: 64,
                                  color: AppColors.textHint),
                              SizedBox(height: 12),
                              Center(
                                child: Text('Tidak ada nasabah',
                                    style: TextStyle(
                                        color: AppColors.textSecondary)),
                              ),
                            ],
                          )
                        : ListView.separated(
                            controller: _scrollCtl,
                            padding: const EdgeInsets.fromLTRB(
                                16, 4, 16, 100),
                            itemCount: _allNasabah.length +
                                (_loadingMore ? 1 : 0),
                            separatorBuilder: (_, __) =>
                                const SizedBox(height: 10),
                            itemBuilder: (_, i) {
                              if (i >= _allNasabah.length) {
                                return const Padding(
                                  padding: EdgeInsets.all(16),
                                  child: Center(
                                      child: CircularProgressIndicator()),
                                );
                              }
                              return _NasabahCard(
                                n: _allNasabah[i],
                                onTap: () => context
                                    .push('/nasabah/${_allNasabah[i].id}'),
                              );
                            },
                          ),
                  ),
          ),
        ],
      ),
      floatingActionButton: (user?.canWriteNasabah == true)
          ? FloatingActionButton.extended(
              onPressed: () => context.push('/nasabah/tambah'),
              icon: const Icon(Icons.add_rounded),
              label: const Text('Tambah'),
            )
          : null,
    );
  }
}

class _NasabahCard extends StatelessWidget {
  final Nasabah n;
  final VoidCallback onTap;
  const _NasabahCard({required this.n, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final color = n.isAktif ? AppColors.primary : AppColors.warning;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(14),
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(14),
          boxShadow: AppShadows.sm,
        ),
        child: Row(
          children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Center(
                child: Text(
                  n.nama.isNotEmpty ? n.nama[0].toUpperCase() : '?',
                  style: TextStyle(
                      color: color,
                      fontSize: 18,
                      fontWeight: FontWeight.w800),
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    n.nama,
                    style: const TextStyle(
                        fontSize: 14.5, fontWeight: FontWeight.w800),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 2),
                  Text(
                    '${n.nasabahId} · ${n.namaDesa}',
                    style: const TextStyle(
                        fontSize: 12,
                        color: AppColors.textSecondary),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(
                  horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Text(
                n.isAktif ? 'AKTIF' : 'CALON',
                style: TextStyle(
                    fontSize: 10.5,
                    fontWeight: FontWeight.w700,
                    color: color),
              ),
            ),
            const SizedBox(width: 6),
            const Icon(Icons.chevron_right_rounded,
                color: AppColors.textHint),
          ],
        ),
      ),
    );
  }
}
