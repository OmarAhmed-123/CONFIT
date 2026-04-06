/**
 * CONFIT CARE - Beneficiary Shopping Experience
 * ==============================================
 * Shopping interface for beneficiaries with budget tracking.
 * Prices are hidden when over budget to maintain dignity.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Heart,
  ShoppingBag,
  Filter,
  Search,
  Grid,
  List,
  ChevronDown,
  Check,
  X,
  AlertCircle,
  Sparkles,
  Package,
  Truck,
  Store,
  CreditCard,
  ArrowRight,
  Clock,
  MapPin,
  User,
  LogOut,
} from 'lucide-react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { careService, SessionContext, Voucher, Campaign, Beneficiary } from '../../services/care.service';
import { Button } from '../../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Progress } from '../../components/ui/progress';
import { Input } from '../../components/ui/input';
import { useBeneficiaryShoppingViewModel } from '../../viewmodels/useBeneficiaryShoppingViewModel';

interface Product {
  id: string;
  name: string;
  brand: string;
  price: number;
  original_price?: number;
  image_url: string;
  category: string;
  sizes: string[];
  colors: string[];
  in_stock: boolean;
}

export const BeneficiaryShopping: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const sessionToken = searchParams.get('session');

  const {
    context,
    products,
    cart,
    loading,
    error,
    budgetRemaining,
    showPrices,
    filters,
    sortBy,
    viewMode,
    fetchContext,
    fetchProducts,
    addToCart,
    removeFromCart,
    updateQuantity,
    applyFilters,
    setSortBy,
    setViewMode,
    checkout,
    logout,
  } = useBeneficiaryShoppingViewModel(sessionToken);

  const [showCart, setShowCart] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    if (sessionToken) {
      fetchContext();
      fetchProducts();
    }
  }, [sessionToken]);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-EG', {
      style: 'currency',
      currency: 'EGP',
      minimumFractionDigits: 0,
    }).format(amount);
  };

  const cartTotal = cart.reduce((sum, item) => sum + item.price * item.quantity, 0);
  const isOverBudget = cartTotal > budgetRemaining;

  const filteredProducts = products.filter((product: Product) => {
    const matchesSearch = product.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = !filters.category || product.category === filters.category;
    const matchesBudget = !showPrices || product.price <= budgetRemaining;
    return matchesSearch && matchesCategory && matchesBudget;
  });

  if (loading && !context) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-pink-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600" />
      </div>
    );
  }

  if (!context) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-pink-50 flex items-center justify-center">
        <Card className="max-w-md">
          <CardContent className="p-8 text-center">
            <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <h2 className="text-xl font-bold mb-2">Session Expired</h2>
            <p className="text-gray-500 mb-4">Your shopping session has expired. Please use your voucher link again.</p>
            <Button onClick={() => navigate('/care/entry')}>
              Start Over
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-pink-50">
      {/* Header */}
      <div className="bg-white/80 backdrop-blur-sm border-b border-purple-100 sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                <Heart className="w-4 h-4 text-white" />
              </div>
              <span className="text-lg font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
                CONFIT CARE
              </span>
            </div>

            {/* Budget Indicator */}
            <div className="flex items-center gap-4">
              <div className="text-right">
                <p className="text-xs text-gray-500">Budget Remaining</p>
                <p className={`text-lg font-bold ${isOverBudget ? 'text-red-500' : 'text-purple-600'}`}>
                  {formatCurrency(budgetRemaining - cartTotal)}
                </p>
              </div>
              
              {/* Cart Button */}
              <Button
                variant="outline"
                className="relative"
                onClick={() => setShowCart(true)}
              >
                <ShoppingBag className="w-5 h-5" />
                {cart.length > 0 && (
                  <span className="absolute -top-2 -right-2 w-5 h-5 bg-purple-600 text-white text-xs rounded-full flex items-center justify-center">
                    {cart.length}
                  </span>
                )}
              </Button>

              {/* Logout */}
              <Button variant="ghost" size="sm" onClick={logout}>
                <LogOut className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Welcome Banner */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6"
        >
          <Card className="bg-gradient-to-r from-purple-500 to-pink-500 text-white border-0">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-2xl font-bold mb-1">
                    Welcome, {context.beneficiary?.name || 'Shopper'}! 
                  </h1>
                  <p className="text-white/80">
                    {context.campaign?.campaign_name || 'Your Shopping Experience'}
                  </p>
                </div>
                <Sparkles className="w-12 h-12 text-white/50" />
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Search and Filters */}
        <div className="flex items-center gap-4 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <Input
              placeholder="Search products..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
          
          <Button
            variant="outline"
            onClick={() => setShowFilters(!showFilters)}
            className={showFilters ? 'bg-purple-50 border-purple-200' : ''}
          >
            <Filter className="w-4 h-4 mr-2" />
            Filters
          </Button>

          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="px-3 py-2 rounded-lg border border-gray-200 text-sm"
            aria-label="Sort products"
            title="Sort by"
          >
            <option value="recommended">Recommended</option>
            <option value="price-low">Price: Low to High</option>
            <option value="price-high">Price: High to Low</option>
            <option value="newest">Newest</option>
          </select>

          <div className="flex items-center border border-gray-200 rounded-lg">
            <Button
              variant={viewMode === 'grid' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setViewMode('grid')}
              className="rounded-r-none"
            >
              <Grid className="w-4 h-4" />
            </Button>
            <Button
              variant={viewMode === 'list' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setViewMode('list')}
              className="rounded-l-none"
            >
              <List className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Filter Panel */}
        <AnimatePresence>
          {showFilters && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="mb-6 overflow-hidden"
            >
              <Card>
                <CardContent className="p-4">
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div>
                      <label className="text-sm font-medium text-gray-700">Category</label>
                      <select
                        value={filters.category || ''}
                        onChange={(e) => applyFilters({ ...filters, category: e.target.value })}
                        className="w-full mt-1 px-3 py-2 rounded-lg border border-gray-200"
                        aria-label="Select category"
                        title="Category"
                      >
                        <option value="">All Categories</option>
                        <option value="tops">Tops</option>
                        <option value="bottoms">Bottoms</option>
                        <option value="dresses">Dresses</option>
                        <option value="outerwear">Outerwear</option>
                        <option value="footwear">Footwear</option>
                        <option value="accessories">Accessories</option>
                      </select>
                    </div>
                    
                    <div>
                      <label className="text-sm font-medium text-gray-700">Size</label>
                      <select
                        value={filters.size || ''}
                        onChange={(e) => applyFilters({ ...filters, size: e.target.value })}
                        className="w-full mt-1 px-3 py-2 rounded-lg border border-gray-200"
                        aria-label="Select size"
                        title="Size"
                      >
                        <option value="">All Sizes</option>
                        <option value="XS">XS</option>
                        <option value="S">S</option>
                        <option value="M">M</option>
                        <option value="L">L</option>
                        <option value="XL">XL</option>
                        <option value="XXL">XXL</option>
                      </select>
                    </div>

                    <div>
                      <label className="text-sm font-medium text-gray-700">Brand</label>
                      <select
                        value={filters.brand || ''}
                        onChange={(e) => applyFilters({ ...filters, brand: e.target.value })}
                        className="w-full mt-1 px-3 py-2 rounded-lg border border-gray-200"
                        aria-label="Select brand"
                        title="Brand"
                      >
                        <option value="">All Brands</option>
                        {/* Dynamic brands would be loaded here */}
                      </select>
                    </div>

                    <div className="flex items-end">
                      <Button
                        variant="outline"
                        onClick={() => applyFilters({})}
                        className="w-full"
                      >
                        Clear Filters
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Products Grid */}
        <div className={viewMode === 'grid' 
          ? "grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4"
          : "space-y-4"
        }>
          {filteredProducts.map((product: Product) => (
            <motion.div
              key={product.id}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className={viewMode === 'grid' ? '' : 'flex'}
            >
              <Card className={`overflow-hidden hover:shadow-lg transition-shadow cursor-pointer ${
                viewMode === 'list' ? 'flex flex-1' : ''
              }`}>
                <div className={viewMode === 'grid' ? 'aspect-square' : 'w-32 h-32'}>
                  <img
                    src={product.image_url}
                    alt={product.name}
                    className="w-full h-full object-cover"
                  />
                </div>
                <CardContent className="p-4">
                  <p className="text-xs text-gray-500 mb-1">{product.brand}</p>
                  <h3 className="font-medium text-gray-900 mb-2 line-clamp-2">{product.name}</h3>
                  
                  {showPrices && (
                    <div className="flex items-center gap-2 mb-2">
                      <span className="font-bold text-purple-600">
                        {formatCurrency(product.price)}
                      </span>
                      {product.original_price && product.original_price > product.price && (
                        <span className="text-sm text-gray-400 line-through">
                          {formatCurrency(product.original_price)}
                        </span>
                      )}
                    </div>
                  )}

                  <div className="flex items-center gap-2 mb-3">
                    {product.sizes.slice(0, 3).map((size) => (
                      <span
                        key={size}
                        className="px-2 py-0.5 text-xs bg-gray-100 rounded"
                      >
                        {size}
                      </span>
                    ))}
                    {product.sizes.length > 3 && (
                      <span className="text-xs text-gray-400">+{product.sizes.length - 3}</span>
                    )}
                  </div>

                  <Button
                    className="w-full"
                    size="sm"
                    onClick={() => addToCart(product)}
                    disabled={!product.in_stock}
                  >
                    {product.in_stock ? 'Add to Cart' : 'Out of Stock'}
                  </Button>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>

        {filteredProducts.length === 0 && (
          <div className="text-center py-12">
            <Package className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">No products found</p>
          </div>
        )}
      </div>

      {/* Cart Drawer */}
      <AnimatePresence>
        {showCart && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/50 z-30"
              onClick={() => setShowCart(false)}
            />
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 20 }}
              className="fixed right-0 top-0 h-full w-full max-w-md bg-white z-40 shadow-xl"
            >
              <div className="flex flex-col h-full">
                {/* Cart Header */}
                <div className="p-4 border-b border-gray-100">
                  <div className="flex items-center justify-between">
                    <h2 className="text-lg font-bold">Your Cart</h2>
                    <Button variant="ghost" size="sm" onClick={() => setShowCart(false)}>
                      <X className="w-5 h-5" />
                    </Button>
                  </div>
                </div>

                {/* Cart Items */}
                <div className="flex-1 overflow-y-auto p-4">
                  {cart.length === 0 ? (
                    <div className="text-center py-12">
                      <ShoppingBag className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                      <p className="text-gray-500">Your cart is empty</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {cart.map((item) => (
                        <div key={item.id} className="flex gap-4 p-3 bg-gray-50 rounded-lg">
                          <img
                            src={item.image_url}
                            alt={item.name}
                            className="w-20 h-20 object-cover rounded"
                          />
                          <div className="flex-1">
                            <h4 className="font-medium">{item.name}</h4>
                            <p className="text-sm text-gray-500">{item.size} · {item.color}</p>
                            {showPrices && (
                              <p className="font-bold text-purple-600">
                                {formatCurrency(item.price)}
                              </p>
                            )}
                            <div className="flex items-center gap-2 mt-2">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => updateQuantity(item.id, item.quantity - 1)}
                              >
                                -
                              </Button>
                              <span className="w-8 text-center">{item.quantity}</span>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => updateQuantity(item.id, item.quantity + 1)}
                              >
                                +
                              </Button>
                            </div>
                          </div>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => removeFromCart(item.id)}
                          >
                            <X className="w-4 h-4" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Cart Footer */}
                {cart.length > 0 && (
                  <div className="p-4 border-t border-gray-100">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-gray-500">Subtotal</span>
                      <span className="font-bold">{formatCurrency(cartTotal)}</span>
                    </div>
                    
                    <div className="flex items-center justify-between mb-4">
                      <span className="text-gray-500">Remaining Budget</span>
                      <span className={`font-bold ${isOverBudget ? 'text-red-500' : 'text-green-500'}`}>
                        {formatCurrency(budgetRemaining - cartTotal)}
                      </span>
                    </div>

                    {isOverBudget && (
                      <div className="p-3 bg-red-50 rounded-lg mb-4">
                        <p className="text-sm text-red-600 flex items-center gap-2">
                          <AlertCircle className="w-4 h-4" />
                          Your cart exceeds your budget by {formatCurrency(cartTotal - budgetRemaining)}
                        </p>
                      </div>
                    )}

                    <Button
                      className="w-full bg-gradient-to-r from-purple-600 to-pink-600"
                      disabled={isOverBudget || cart.length === 0}
                      onClick={() => checkout()}
                    >
                      Proceed to Checkout
                      <ArrowRight className="w-4 h-4 ml-2" />
                    </Button>
                  </div>
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
};

export default BeneficiaryShopping;
