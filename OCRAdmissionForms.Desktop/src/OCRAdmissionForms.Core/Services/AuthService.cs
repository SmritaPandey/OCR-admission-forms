using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using Microsoft.EntityFrameworkCore;
using OCRAdmissionForms.Core.Data;
using OCRAdmissionForms.Core.Entities;

namespace OCRAdmissionForms.Core.Services;

/// <summary>
/// Authentication service with offline support and role-based access
/// </summary>
public class AuthService
{
    private static readonly string CachePath;
    private const int SaltSize = 16;
    private const int HashSize = 32;
    private const int Iterations = 100000;

    private User? _currentUser;

    static AuthService()
    {
        var appData = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
        var dataFolder = Path.Combine(appData, "SRCC Student DMS", "data");
        Directory.CreateDirectory(dataFolder);
        CachePath = Path.Combine(dataFolder, ".auth_cache");
    }

    /// <summary>
    /// Currently logged in user
    /// </summary>
    public User? CurrentUser => _currentUser;

    /// <summary>
    /// Check if user is authenticated
    /// </summary>
    public bool IsAuthenticated => _currentUser != null;

    /// <summary>
    /// Check if current user has specified role
    /// </summary>
    public bool HasRole(UserRole role) => _currentUser?.Role == role;

    /// <summary>
    /// Check if current user is admin
    /// </summary>
    public bool IsAdmin => _currentUser?.Role == UserRole.Admin;

    /// <summary>
    /// Authenticate user with username and password
    /// </summary>
    public async Task<AuthResult> LoginAsync(string username, string password)
    {
        using var context = new AppDbContext();
        
        var user = await context.Users
            .FirstOrDefaultAsync(u => u.Username == username && u.IsActive);
        
        if (user == null)
        {
            // Try cached credentials for offline login
            return TryOfflineLogin(username, password);
        }

        if (!VerifyPassword(password, user.PasswordHash, user.Salt))
        {
            return new AuthResult { Success = false, Error = "Invalid password" };
        }

        // Update last login
        user.LastLoginDate = DateTime.UtcNow;
        await context.SaveChangesAsync();

        _currentUser = user;
        
        // Cache for offline login
        CacheCredentials(username, password, user);

        return new AuthResult 
        { 
            Success = true, 
            User = user,
            Message = $"Welcome, {user.FullName}!"
        };
    }

    /// <summary>
    /// Logout current user
    /// </summary>
    public void Logout()
    {
        _currentUser = null;
    }

    /// <summary>
    /// Register a new user (Admin only)
    /// </summary>
    public async Task<AuthResult> RegisterUserAsync(
        string username, 
        string password, 
        string fullName, 
        UserRole role,
        string? department = null,
        string? email = null)
    {
        if (!IsAdmin && await HasAnyUsersAsync())
        {
            return new AuthResult { Success = false, Error = "Only admins can create users" };
        }

        using var context = new AppDbContext();

        if (await context.Users.AnyAsync(u => u.Username == username))
        {
            return new AuthResult { Success = false, Error = "Username already exists" };
        }

        var salt = GenerateSalt();
        var hash = HashPassword(password, salt);

        var user = new User
        {
            Username = username,
            PasswordHash = hash,
            Salt = salt,
            FullName = fullName,
            Email = email,
            Role = role,
            Department = department,
            IsActive = true,
            CreatedDate = DateTime.UtcNow
        };

        context.Users.Add(user);
        await context.SaveChangesAsync();

        return new AuthResult 
        { 
            Success = true, 
            User = user,
            Message = "User created successfully"
        };
    }

    /// <summary>
    /// Change password for current user
    /// </summary>
    public async Task<AuthResult> ChangePasswordAsync(string currentPassword, string newPassword)
    {
        if (_currentUser == null)
        {
            return new AuthResult { Success = false, Error = "Not authenticated" };
        }

        using var context = new AppDbContext();
        var user = await context.Users.FindAsync(_currentUser.Id);
        
        if (user == null)
        {
            return new AuthResult { Success = false, Error = "User not found" };
        }

        if (!VerifyPassword(currentPassword, user.PasswordHash, user.Salt))
        {
            return new AuthResult { Success = false, Error = "Current password is incorrect" };
        }

        var salt = GenerateSalt();
        user.PasswordHash = HashPassword(newPassword, salt);
        user.Salt = salt;
        await context.SaveChangesAsync();

        _currentUser = user;

        return new AuthResult { Success = true, Message = "Password changed successfully" };
    }

    /// <summary>
    /// Ensure default admin exists on first run
    /// </summary>
    public async Task EnsureDefaultAdminAsync()
    {
        using var context = new AppDbContext();
        await context.Database.EnsureCreatedAsync();

        if (!await context.Users.AnyAsync())
        {
            var salt = GenerateSalt();
            var hash = HashPassword("admin123", salt);

            var admin = new User
            {
                Username = "admin",
                PasswordHash = hash,
                Salt = salt,
                FullName = "System Administrator",
                Email = "admin@srcc.du.ac.in",
                Role = UserRole.Admin,
                Department = "IT",
                IsActive = true,
                CreatedDate = DateTime.UtcNow
            };

            context.Users.Add(admin);
            await context.SaveChangesAsync();
        }
    }

    /// <summary>
    /// Get all users (Admin only)
    /// </summary>
    public async Task<User[]> GetAllUsersAsync()
    {
        if (!IsAdmin) return Array.Empty<User>();

        using var context = new AppDbContext();
        return await context.Users.ToArrayAsync();
    }

    /// <summary>
    /// Check if any users exist
    /// </summary>
    public async Task<bool> HasAnyUsersAsync()
    {
        using var context = new AppDbContext();
        return await context.Users.AnyAsync();
    }

    #region Password Hashing

    private static string GenerateSalt()
    {
        var salt = new byte[SaltSize];
        using var rng = RandomNumberGenerator.Create();
        rng.GetBytes(salt);
        return Convert.ToBase64String(salt);
    }

    private static string HashPassword(string password, string salt)
    {
        var saltBytes = Convert.FromBase64String(salt);
        using var pbkdf2 = new Rfc2898DeriveBytes(
            password, 
            saltBytes, 
            Iterations, 
            HashAlgorithmName.SHA512);
        var hash = pbkdf2.GetBytes(HashSize);
        return Convert.ToBase64String(hash);
    }

    private static bool VerifyPassword(string password, string hash, string salt)
    {
        var computedHash = HashPassword(password, salt);
        return computedHash == hash;
    }

    #endregion

    #region Offline Cache

    private static readonly byte[] AesKey = Encoding.UTF8.GetBytes("SRCC_DMS_KEY_32B_ENCRYPT_2026!!");
    private static readonly byte[] AesIv = Encoding.UTF8.GetBytes("SRCC_DMS_IV_16!!");

    private static void CacheCredentials(string username, string password, User user)
    {
        try
        {
            var cache = new OfflineAuthCache
            {
                Username = username,
                PasswordHash = HashPassword(password, user.Salt),
                Salt = user.Salt,
                UserData = JsonSerializer.Serialize(user),
                CachedAt = DateTime.UtcNow
            };
            
            var json = JsonSerializer.Serialize(cache);
            var encrypted = EncryptAes(json);
            
            File.WriteAllBytes(CachePath, encrypted);
        }
        catch
        {
            // Cache is optional, fail silently
        }
    }

    private AuthResult TryOfflineLogin(string username, string password)
    {
        try
        {
            if (!File.Exists(CachePath))
            {
                return new AuthResult { Success = false, Error = "User not found", IsOffline = true };
            }

            var encrypted = File.ReadAllBytes(CachePath);
            var json = DecryptAes(encrypted);
            var cache = JsonSerializer.Deserialize<OfflineAuthCache>(json);

            if (cache == null || cache.Username != username)
            {
                return new AuthResult { Success = false, Error = "User not found", IsOffline = true };
            }

            // Check if cache is too old (7 days)
            if ((DateTime.UtcNow - cache.CachedAt).TotalDays > 7)
            {
                return new AuthResult { Success = false, Error = "Offline cache expired", IsOffline = true };
            }

            if (!VerifyPassword(password, cache.PasswordHash, cache.Salt))
            {
                return new AuthResult { Success = false, Error = "Invalid password", IsOffline = true };
            }

            _currentUser = JsonSerializer.Deserialize<User>(cache.UserData ?? "{}");

            return new AuthResult 
            { 
                Success = true, 
                User = _currentUser,
                Message = "Logged in offline",
                IsOffline = true
            };
        }
        catch
        {
            return new AuthResult { Success = false, Error = "Offline login failed", IsOffline = true };
        }
    }

    private static byte[] EncryptAes(string plainText)
    {
        using var aes = Aes.Create();
        aes.Key = AesKey;
        aes.IV = AesIv;
        
        using var encryptor = aes.CreateEncryptor();
        var plainBytes = Encoding.UTF8.GetBytes(plainText);
        return encryptor.TransformFinalBlock(plainBytes, 0, plainBytes.Length);
    }

    private static string DecryptAes(byte[] cipherText)
    {
        using var aes = Aes.Create();
        aes.Key = AesKey;
        aes.IV = AesIv;
        
        using var decryptor = aes.CreateDecryptor();
        var plainBytes = decryptor.TransformFinalBlock(cipherText, 0, cipherText.Length);
        return Encoding.UTF8.GetString(plainBytes);
    }

    private class OfflineAuthCache
    {
        public string Username { get; set; } = string.Empty;
        public string PasswordHash { get; set; } = string.Empty;
        public string Salt { get; set; } = string.Empty;
        public string? UserData { get; set; }
        public DateTime CachedAt { get; set; }
    }

    #endregion
}

public class AuthResult
{
    public bool Success { get; set; }
    public string? Error { get; set; }
    public string? Message { get; set; }
    public User? User { get; set; }
    public bool IsOffline { get; set; }
}
