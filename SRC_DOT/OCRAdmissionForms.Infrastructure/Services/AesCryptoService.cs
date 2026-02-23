using System;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using Microsoft.Extensions.Configuration;
using OCRAdmissionForms.Core.Interfaces;

namespace OCRAdmissionForms.Infrastructure.Services;

public class AesCryptoService : ICryptoService
{
    private readonly byte[] _key;
    private readonly byte[] _iv;

    public AesCryptoService(IConfiguration configuration)
    {
        // In a real app, load from secure config (Azure KeyVault, Environment)
        // For this replica, we'll derive from a fixed or config string
        var secret = configuration["EncryptionKey"] ?? "DefaultSuperSecretKey123456789012";
        
        // Ensure 32 bytes for AES-256
        using var sha = SHA256.Create();
        _key = sha.ComputeHash(Encoding.UTF8.GetBytes(secret));
        
        // Use a fixed IV or derived one. For simplicity in this demo, using first 16 bytes of key
        // In production, IV should be random and stored with ciphertext
        _iv = new byte[16];
        Array.Copy(_key, _iv, 16);
    }

    public string Encrypt(string plainText)
    {
        if (string.IsNullOrEmpty(plainText)) return plainText;

        using var aes = Aes.Create();
        aes.Key = _key;
        aes.IV = _iv;

        using var encryptor = aes.CreateEncryptor(aes.Key, aes.IV);
        using var ms = new MemoryStream();
        using (var cs = new CryptoStream(ms, encryptor, CryptoStreamMode.Write))
        using (var sw = new StreamWriter(cs))
        {
            sw.Write(plainText);
        }

        return Convert.ToBase64String(ms.ToArray());
    }

    public string Decrypt(string cipherText)
    {
        if (string.IsNullOrEmpty(cipherText)) return cipherText;

        try
        {
            using var aes = Aes.Create();
            aes.Key = _key;
            aes.IV = _iv;

            using var decryptor = aes.CreateDecryptor(aes.Key, aes.IV);
            using var ms = new MemoryStream(Convert.FromBase64String(cipherText));
            using var cs = new CryptoStream(ms, decryptor, CryptoStreamMode.Read);
            using var sr = new StreamReader(cs);
            return sr.ReadToEnd();
        }
        catch
        {
            // Fail gracefully or throw
            return string.Empty;
        }
    }
}
