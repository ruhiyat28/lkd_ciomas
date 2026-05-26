import 'package:intl/intl.dart';

extension CurrencyFormat on int {
  String get toCurrency {
    return NumberFormat('#,###', 'id_ID').format(this);
  }

  String get toCurrencyRp {
    return 'Rp ${NumberFormat('#,###', 'id_ID').format(this)}';
  }
}

extension DoubleCurrencyFormat on double {
  String get toCurrency {
    return NumberFormat('#,###', 'id_ID').format(this);
  }

  String get toCurrencyRp {
    return 'Rp ${NumberFormat('#,###', 'id_ID').format(this)}';
  }
}
